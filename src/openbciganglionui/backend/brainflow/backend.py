from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QCoreApplication, QMetaObject, QObject, QThread, Qt, pyqtSignal

from ..base import GanglionBackendBase
from ..models import (
    ConnectConfig,
    DeviceSearchResult,
    DeviceState,
    ErrorEvent,
    LabelsEvent,
    RecordSession,
    SaveDirEvent,
    SearchEvent,
    StateEvent,
    StreamChunk,
)
from .discovery import DONGLE_METHOD, NATIVE_BLE_METHOD, discover_devices
from .recording_session import BrainFlowRecordingSessionService
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
    """Deprecated legacy BrainFlow backend used by the transitional UI.

    New device-facing integrations should prefer ``adapters.BrainFlowGanglionAdapter``.
    """

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

        self._recording_service = BrainFlowRecordingSessionService(
            emit_record=self.sig_record.emit,
            emit_marker=self.sig_marker.emit,
            emit_segment=self.sig_segment.emit,
            emit_error=self.sig_error.emit,
            emit_fatal_error=self._emit_error,
            request_insert_marker=self._request_insert_marker.emit,
            set_state=self._set_state,
        )

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

        if self._recording_service.is_recording:
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

        if self._recording_service.is_recording:
            self.stop_record()

        self._request_stop_preview.emit()

    def start_record(self, session: Optional[RecordSession] = None) -> None:
        self._recording_service.start_record(
            session,
            current_state=self._state,
            default_save_dir=self._default_save_dir,
            sample_index=self._sample_index,
        )

    def stop_record(self) -> None:
        self._recording_service.stop_record(
            current_state=self._state,
            sample_index=self._sample_index,
            fs=self._fs,
            channel_names=self._channel_names,
        )

    def add_marker(self, label: str, note: str = "", source: str = "ui") -> None:
        self._recording_service.add_marker(
            label,
            note,
            source,
            current_state=self._state,
            sample_index=self._sample_index,
        )

    def start_segment(self, label: str, note: str = "", source: str = "ui") -> None:
        self._recording_service.start_segment(
            label,
            note,
            source,
            current_state=self._state,
            sample_index=self._sample_index,
        )

    def stop_segment(self, note: str = "", source: str = "ui") -> None:
        self._recording_service.stop_segment(
            note,
            source,
            current_state=self._state,
            sample_index=self._sample_index,
        )

    def _run_search(self, method: str, token: int) -> None:
        try:
            results = tuple(
                discover_devices(
                    method,
                    timeout_sec=min(5.0, float(self._config.timeout_sec)),
                )
            )
            self._search_completed.emit(
                _SearchCompleted(method=method, token=token, results=results)
            )
        except Exception as exc:
            self._search_failed.emit(
                _SearchFailed(method=method, token=token, detail=str(exc))
            )

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

        self._recording_service.append_stream_chunk(payload.data)

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

        if self._recording_service.is_recording:
            self._recording_service.finalize_after_error(
                current_state=self._state,
                sample_index=self._sample_index,
                fs=self._fs,
                channel_names=self._channel_names,
            )

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
