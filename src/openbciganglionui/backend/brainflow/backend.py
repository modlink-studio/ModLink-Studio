from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
from PyQt6.QtCore import QCoreApplication, QMetaObject, QObject, QThread, Qt, pyqtSignal

from ..base import GanglionBackendBase
from ..models import (
    ConnectConfig,
    DeviceSearchResult,
    DeviceState,
    ErrorEvent,
    LabelsEvent,
    MarkerEvent,
    RecordEvent,
    RecordingMode,
    RecordSegment,
    RecordSession,
    SaveDirEvent,
    SearchEvent,
    SegmentEvent,
    StateEvent,
    StreamChunk,
)
from ..record_writer import RecordWriteRequest, SessionRecordWriter
from .discovery import DONGLE_METHOD, NATIVE_BLE_METHOD, discover_devices
from .marker_codec import MarkerCodec
from .worker import BrainFlowWorker, WorkerChunk, WorkerConnectionInfo, WorkerFailure


@dataclass(slots=True)
class _SearchCompleted:
    method: str
    token: int
    results: tuple[DeviceSearchResult, ...]


@dataclass(slots=True)
class _SearchFailed:
    method: str
    token: int
    detail: str


class BrainFlowGanglionBackend(GanglionBackendBase):
    """BrainFlow-powered backend that preserves the UI-facing backend contract."""

    _request_connect = pyqtSignal(object)
    _request_start_preview = pyqtSignal(int)
    _request_stop_preview = pyqtSignal()
    _request_disconnect = pyqtSignal()
    _request_insert_marker = pyqtSignal(float)
    _search_completed = pyqtSignal(object)
    _search_failed = pyqtSignal(object)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)

        self._state = DeviceState.DISCONNECTED
        self._device_name = ""
        self._device_address = ""
        self._labels = self._default_labels()
        self._default_save_dir = self._default_recording_dir()

        self._config = ConnectConfig(device_name="Ganglion")
        self._fs = float(self._config.fs)
        self._channel_names: tuple[str, ...] = tuple(
            f"ch{index + 1}" for index in range(self._config.n_channels)
        )
        self._seq = 0
        self._sample_index = 0

        self._is_recording = False
        self._record_session: Optional[RecordSession] = None
        self._record_buffer: list[np.ndarray] = []
        self._markers: list[MarkerEvent] = []
        self._segments: list[RecordSegment] = []
        self._active_segment: Optional[RecordSegment] = None
        self._record_start_sample_index = 0
        self._record_writer = SessionRecordWriter()
        self._marker_codec = MarkerCodec()

        self._search_token = 0
        self._is_searching = False
        self._worker_thread_stopped = False

        self._worker_thread = QThread(self)
        self._worker = BrainFlowWorker()
        self._worker.moveToThread(self._worker_thread)

        self._request_connect.connect(
            self._worker.connect_device,
            Qt.ConnectionType.QueuedConnection,
        )
        self._request_start_preview.connect(
            self._worker.start_preview,
            Qt.ConnectionType.QueuedConnection,
        )
        self._request_stop_preview.connect(
            self._worker.stop_preview,
            Qt.ConnectionType.QueuedConnection,
        )
        self._request_disconnect.connect(
            self._worker.disconnect_device,
            Qt.ConnectionType.QueuedConnection,
        )
        self._request_insert_marker.connect(
            self._worker.insert_marker,
            Qt.ConnectionType.QueuedConnection,
        )

        self._worker.sig_connected.connect(self._on_worker_connected)
        self._worker.sig_preview_started.connect(self._on_worker_preview_started)
        self._worker.sig_preview_stopped.connect(self._on_worker_preview_stopped)
        self._worker.sig_stream.connect(self._on_worker_stream)
        self._worker.sig_disconnected.connect(self._on_worker_disconnected)
        self._worker.sig_error.connect(self._on_worker_error)
        self._search_completed.connect(self._on_search_completed)
        self._search_failed.connect(self._on_search_failed)

        self._worker_thread.start()

        app = QCoreApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self._shutdown_worker_thread)

    @property
    def state(self) -> DeviceState:
        return self._state

    @property
    def device_name(self) -> str:
        return self._device_name

    @property
    def device_address(self) -> str:
        return self._device_address

    @property
    def labels(self) -> tuple[str, ...]:
        return tuple(self._labels)

    @property
    def default_save_dir(self) -> str:
        return self._default_save_dir

    def connect_device(self, config: Optional[ConnectConfig] = None) -> None:
        if self._state not in {DeviceState.DISCONNECTED, DeviceState.ERROR}:
            return

        normalized = config or self._config
        if int(normalized.chunk_size) <= 0:
            self._emit_error(
                code="INVALID_CONFIG",
                message="chunk_size 必须大于 0",
                detail=f"got chunk_size={normalized.chunk_size}",
            )
            return

        if str(normalized.connection_method).strip() == DONGLE_METHOD:
            serial_port = (normalized.serial_port or normalized.device_address).strip()
            if not serial_port:
                self._emit_error(
                    code="INVALID_CONFIG",
                    message="Ganglion Dongle 连接必须提供串口",
                    detail="missing serial_port",
                )
                return

        self._config = normalized
        self._device_name = str(normalized.device_name).strip()
        self._device_address = self._display_address(normalized)
        self._set_state(DeviceState.CONNECTING, "正在连接 BrainFlow 设备...")
        self._request_connect.emit(self._config)

    def search_devices(self, method: str) -> None:
        if self._state not in {DeviceState.DISCONNECTED, DeviceState.ERROR}:
            return
        if self._is_searching:
            return

        normalized_method = str(method).strip() or NATIVE_BLE_METHOD
        self._is_searching = True
        self._search_token += 1
        token = self._search_token

        self.sig_search.emit(
            SearchEvent(
                method=normalized_method,
                is_searching=True,
                ts=time.time(),
                message="正在搜索设备...",
            )
        )

        thread = threading.Thread(
            target=self._run_search,
            args=(normalized_method, token),
            daemon=True,
        )
        thread.start()

    def load_labels(self) -> None:
        self._emit_labels("标签已加载")

    def add_label(self, label: str) -> None:
        normalized = label.strip()
        if not normalized:
            return

        if normalized in self._labels:
            self._emit_labels("标签已存在")
            return

        self._labels.append(normalized)
        self._emit_labels("标签已添加")

    def remove_label(self, label: str) -> None:
        normalized = label.strip()
        if normalized not in self._labels:
            return

        self._labels.remove(normalized)
        self._emit_labels("标签已删除")

    def load_save_dir(self) -> None:
        self._emit_save_dir("保存目录已加载")

    def set_save_dir(self, save_dir: str) -> None:
        normalized = str(Path(save_dir).expanduser()).strip()
        if not normalized:
            return

        self._default_save_dir = normalized
        self._emit_save_dir("保存目录已更新")

    def disconnect_device(self) -> None:
        if self._state not in {
            DeviceState.CONNECTED,
            DeviceState.PREVIEWING,
            DeviceState.RECORDING,
        }:
            return

        if self._is_recording:
            self.stop_record()

        self._set_state(DeviceState.DISCONNECTING, "正在断开设备...")
        self._request_disconnect.emit()

    def start_preview(self) -> None:
        if self._state != DeviceState.CONNECTED:
            return

        self._request_start_preview.emit(self._preview_interval_ms())

    def stop_preview(self) -> None:
        if self._state not in {DeviceState.PREVIEWING, DeviceState.RECORDING}:
            return

        if self._is_recording:
            self.stop_record()

        self._request_stop_preview.emit()

    def start_record(self, session: Optional[RecordSession] = None) -> None:
        if self._state != DeviceState.PREVIEWING:
            return

        if session is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            session = RecordSession(
                session_id=timestamp,
                save_dir=self._default_save_dir,
                subject_id=f"session_{timestamp}",
                task_name="default_label",
            )

        built_session = self._build_record_session(session)

        try:
            Path(built_session.save_dir).mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            self._emit_error(
                code="RECORD_DIR_ERROR",
                message="无法创建录制目录",
                detail=str(exc),
            )
            return

        self._record_session = built_session
        self._record_buffer.clear()
        self._markers.clear()
        self._segments.clear()
        self._active_segment = None
        self._marker_codec = MarkerCodec()
        self._is_recording = True
        self._record_start_sample_index = self._sample_index

        self.sig_record.emit(
            RecordEvent(
                is_recording=True,
                ts=time.time(),
                session_id=built_session.session_id,
                save_dir=built_session.save_dir,
                sample_index=self._sample_index,
                recording_mode=built_session.recording_mode,
            )
        )
        message = (
            "开始片段录制"
            if built_session.recording_mode == RecordingMode.CLIP
            else "开始连续录制"
        )
        self._set_state(DeviceState.RECORDING, message)

    def stop_record(self) -> None:
        if not self._is_recording:
            return

        if (
            self._record_session is not None
            and self._record_session.recording_mode == RecordingMode.CONTINUOUS
        ):
            self.stop_segment(note="auto_closed_on_stop", source="system")

        self._persist_record_buffer()

        session = self._record_session
        self._is_recording = False
        self._record_session = None
        self._record_buffer.clear()
        self._active_segment = None

        self.sig_record.emit(
            RecordEvent(
                is_recording=False,
                ts=time.time(),
                session_id=session.session_id if session else None,
                save_dir=session.save_dir if session else None,
                sample_index=self._sample_index,
                recording_mode=session.recording_mode if session else RecordingMode.CLIP,
            )
        )

        if self._state == DeviceState.DISCONNECTING:
            return
        self._set_state(DeviceState.PREVIEWING, "停止录制")

    def add_marker(self, label: str, note: str = "", source: str = "ui") -> None:
        if self._state != DeviceState.RECORDING or self._record_session is None:
            return

        if self._record_session.recording_mode != RecordingMode.CLIP:
            return

        normalized_label = label.strip() or "marker"
        event = MarkerEvent(
            marker_id=f"m_{uuid.uuid4().hex[:8]}",
            label=normalized_label,
            wall_time=time.time(),
            sample_index=self._sample_index,
            note=note,
            source=source,
        )
        self._markers.append(event)
        self.sig_marker.emit(event)

        try:
            self._request_insert_marker.emit(self._marker_codec.encode(normalized_label))
        except ValueError:
            pass

    def start_segment(self, label: str, note: str = "", source: str = "ui") -> None:
        if self._state != DeviceState.RECORDING or self._record_session is None:
            return

        if self._record_session.recording_mode != RecordingMode.CONTINUOUS:
            return

        if self._active_segment is not None:
            return

        normalized_label = self._normalize_record_component(label, fallback="default_label")
        event_time = time.time()
        segment = RecordSegment(
            segment_id=f"s_{uuid.uuid4().hex[:8]}",
            label=normalized_label,
            start_sample_index=self._sample_index,
            started_at=event_time,
            note=note,
            source=source,
        )
        self._segments.append(segment)
        self._active_segment = segment
        self.sig_segment.emit(
            SegmentEvent(
                action="started",
                segment_id=segment.segment_id,
                label=segment.label,
                ts=event_time,
                start_sample_index=segment.start_sample_index,
                session_id=self._record_session.session_id,
                note=segment.note,
                source=segment.source,
            )
        )

    def stop_segment(self, note: str = "", source: str = "ui") -> None:
        if self._state != DeviceState.RECORDING or self._record_session is None:
            return

        if self._record_session.recording_mode != RecordingMode.CONTINUOUS:
            return

        if self._active_segment is None:
            return

        event_time = time.time()
        self._active_segment.end_sample_index = self._sample_index
        self._active_segment.ended_at = event_time
        if note:
            self._active_segment.note = (
                f"{self._active_segment.note} | {note}"
                if self._active_segment.note
                else note
            )

        self.sig_segment.emit(
            SegmentEvent(
                action="stopped",
                segment_id=self._active_segment.segment_id,
                label=self._active_segment.label,
                ts=event_time,
                start_sample_index=self._active_segment.start_sample_index,
                end_sample_index=self._active_segment.end_sample_index,
                session_id=self._record_session.session_id,
                note=self._active_segment.note,
                source=source,
            )
        )
        self._active_segment = None

    def _run_search(self, method: str, token: int) -> None:
        try:
            results = tuple(
                discover_devices(
                    method,
                    timeout_sec=min(5.0, float(self._config.timeout_sec)),
                )
            )
            self._search_completed.emit(_SearchCompleted(method=method, token=token, results=results))
        except Exception as exc:
            self._search_failed.emit(_SearchFailed(method=method, token=token, detail=str(exc)))

    def _on_search_completed(self, payload: _SearchCompleted) -> None:
        if payload.token != self._search_token:
            return

        self._is_searching = False
        self.sig_search.emit(
            SearchEvent(
                method=payload.method,
                is_searching=False,
                ts=time.time(),
                results=payload.results,
                message=f"已搜索到 {len(payload.results)} 个设备",
            )
        )

    def _on_search_failed(self, payload: _SearchFailed) -> None:
        if payload.token != self._search_token:
            return

        self._is_searching = False
        self.sig_search.emit(
            SearchEvent(
                method=payload.method,
                is_searching=False,
                ts=time.time(),
                results=(),
                message="设备搜索失败",
            )
        )
        self.sig_error.emit(
            ErrorEvent(
                code="SEARCH_FAILED",
                message="搜索设备失败",
                ts=time.time(),
                detail=payload.detail,
                recoverable=True,
            )
        )

    def _on_worker_connected(self, info: WorkerConnectionInfo) -> None:
        self._reset_stream_runtime()
        self._fs = info.fs
        self._channel_names = info.channel_names
        self._device_name = info.device_name
        self._device_address = info.device_address
        self._set_state(DeviceState.CONNECTED, "设备已连接")
        self.start_preview()

    def _on_worker_preview_started(self) -> None:
        if self._state in {DeviceState.CONNECTED, DeviceState.PREVIEWING}:
            self._set_state(DeviceState.PREVIEWING, "开始预览")

    def _on_worker_preview_stopped(self) -> None:
        if self._state == DeviceState.DISCONNECTING:
            return
        if self._state in {DeviceState.PREVIEWING, DeviceState.CONNECTED}:
            self._set_state(DeviceState.CONNECTED, "停止预览")

    def _on_worker_stream(self, payload: WorkerChunk) -> None:
        n_samples = int(payload.data.shape[0])
        if n_samples <= 0:
            return

        chunk = StreamChunk(
            seq=self._seq,
            sample_index0=self._sample_index,
            fs=self._fs,
            channel_names=self._channel_names,
            data=payload.data,
            received_at=payload.received_at,
        )
        self._seq += 1
        self._sample_index += n_samples

        if self._is_recording:
            self._record_buffer.append(payload.data.copy())

        self.sig_stream.emit(chunk)

    def _on_worker_disconnected(self) -> None:
        self._reset_stream_runtime()
        self._device_name = ""
        self._device_address = ""
        self._set_state(DeviceState.DISCONNECTED, "设备已断开")

    def _on_worker_error(self, failure: WorkerFailure) -> None:
        self.sig_error.emit(
            ErrorEvent(
                code=failure.code,
                message=failure.message,
                ts=time.time(),
                detail=failure.detail,
                recoverable=failure.recoverable,
            )
        )

        if not failure.transition_to_error:
            return

        if self._is_recording:
            self._finalize_recording_after_error()

        self._state = DeviceState.ERROR
        self.sig_state.emit(
            StateEvent(
                state=DeviceState.ERROR,
                ts=time.time(),
                message=failure.message,
                device_name=self._device_name,
                device_address=self._device_address,
            )
        )

    def _persist_record_buffer(self) -> None:
        if self._record_session is None:
            return

        try:
            self._record_writer.write(
                RecordWriteRequest(
                    session=self._record_session,
                    fs=self._fs,
                    channel_names=self._channel_names,
                    record_start_sample_index=self._record_start_sample_index,
                    stream_sample_index=self._sample_index,
                    data_chunks=tuple(self._record_buffer),
                    markers=tuple(self._markers),
                    segments=tuple(self._segments),
                    marker_codebook=self._marker_codec.snapshot(),
                )
            )
        except Exception as exc:
            self.sig_error.emit(
                ErrorEvent(
                    code="RECORD_WRITE_ERROR",
                    message="录制文件写入失败",
                    ts=time.time(),
                    detail=str(exc),
                    recoverable=True,
                )
            )

    def _finalize_recording_after_error(self) -> None:
        if not self._is_recording:
            return

        if (
            self._record_session is not None
            and self._record_session.recording_mode == RecordingMode.CONTINUOUS
            and self._active_segment is not None
        ):
            self.stop_segment(note="auto_closed_on_error", source="system")

        self._persist_record_buffer()
        session = self._record_session
        self._is_recording = False
        self._record_session = None
        self._record_buffer.clear()
        self._active_segment = None
        self.sig_record.emit(
            RecordEvent(
                is_recording=False,
                ts=time.time(),
                session_id=session.session_id if session else None,
                save_dir=session.save_dir if session else None,
                sample_index=self._sample_index,
                recording_mode=session.recording_mode if session else RecordingMode.CLIP,
            )
        )

    def _build_record_session(self, session: RecordSession) -> RecordSession:
        recording_mode = self._normalize_recording_mode(session.recording_mode)
        default_task_name = (
            "default_label" if recording_mode == RecordingMode.CLIP else "continuous_session"
        )

        session_id = self._normalize_record_component(
            session.session_id,
            fallback=time.strftime("%Y%m%d_%H%M%S"),
        )
        return RecordSession(
            session_id=session_id,
            save_dir=session.save_dir or self._default_save_dir,
            subject_id=self._normalize_record_component(
                session.subject_id,
                fallback=f"session_{session_id}",
            ),
            task_name=self._normalize_record_component(
                session.task_name,
                fallback=default_task_name,
            ),
            recording_mode=recording_mode,
            operator=session.operator,
            notes=session.notes,
        )

    def _preview_interval_ms(self) -> int:
        fs = self._fs if self._fs > 0 else float(self._config.fs)
        chunk_size = max(1, int(self._config.chunk_size))
        return max(1, int(round(1000 * chunk_size / fs)))

    def _display_address(self, config: ConnectConfig) -> str:
        for candidate in (
            config.device_address,
            config.mac_address,
            config.serial_port,
            config.serial_number,
        ):
            normalized = str(candidate).strip()
            if normalized:
                return normalized
        return ""

    def _reset_stream_runtime(self) -> None:
        self._seq = 0
        self._sample_index = 0

    def _default_labels(self) -> list[str]:
        return ["dry_swallow", "water_5ml", "cough"]

    def _default_recording_dir(self) -> str:
        return str((Path.cwd() / "data").resolve())

    def _emit_labels(self, message: str = "") -> None:
        self.sig_labels.emit(
            LabelsEvent(
                labels=tuple(self._labels),
                ts=time.time(),
                storage_path="",
                message=message,
            )
        )

    def _emit_save_dir(self, message: str = "") -> None:
        self.sig_save_dir.emit(
            SaveDirEvent(
                save_dir=self._default_save_dir,
                ts=time.time(),
                message=message,
            )
        )

    def _normalize_recording_mode(self, value: RecordingMode | str) -> RecordingMode:
        if isinstance(value, RecordingMode):
            return value
        try:
            return RecordingMode(str(value).strip())
        except ValueError:
            return RecordingMode.CLIP

    def _normalize_record_component(self, value: str, fallback: str) -> str:
        normalized = str(value).strip()
        if not normalized:
            normalized = fallback

        for char in '<>:"/\\|?*':
            normalized = normalized.replace(char, "_")

        normalized = normalized.rstrip(". ")
        return normalized or fallback

    def _set_state(self, state: DeviceState, message: str = "") -> None:
        self._state = state
        self.sig_state.emit(
            StateEvent(
                state=state,
                ts=time.time(),
                message=message,
                device_name=self._device_name,
                device_address=self._device_address,
            )
        )

    def _emit_error(
        self,
        code: str,
        message: str,
        detail: str = "",
        recoverable: bool = True,
    ) -> None:
        self._state = DeviceState.ERROR
        self.sig_error.emit(
            ErrorEvent(
                code=code,
                message=message,
                ts=time.time(),
                detail=detail,
                recoverable=recoverable,
            )
        )
        self.sig_state.emit(
            StateEvent(
                state=DeviceState.ERROR,
                ts=time.time(),
                message=message,
                device_name=self._device_name,
                device_address=self._device_address,
            )
        )

    def _shutdown_worker_thread(self) -> None:
        if self._worker_thread_stopped or not self._worker_thread.isRunning():
            return

        self._worker_thread_stopped = True
        try:
            QMetaObject.invokeMethod(
                self._worker,
                "shutdown",
                Qt.ConnectionType.BlockingQueuedConnection,
            )
        except RuntimeError:
            pass

        self._worker_thread.quit()
        self._worker_thread.wait(3000)
