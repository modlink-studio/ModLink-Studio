from __future__ import annotations

import math
import json
import time
import uuid
from pathlib import Path
from typing import Optional

import numpy as np
from PyQt6.QtCore import QObject, QStandardPaths, QTimer

from .base import GanglionBackendBase
from .models import (
    ConnectConfig,
    DeviceSearchResult,
    DeviceState,
    ErrorEvent,
    LabelsEvent,
    MarkerEvent,
    RecordEvent,
    RecordSession,
    SearchEvent,
    StateEvent,
    StreamChunk,
)


class MockGanglionBackend(GanglionBackendBase):
    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)

        self._state = DeviceState.DISCONNECTED
        self._device_name = "Ganglion Mock"
        self._device_address = ""
        self._labels_path = self._resolve_labels_path()
        self._labels = self._read_labels_from_disk()

        self._config = ConnectConfig()
        self._channel_names: tuple[str, ...] = tuple(
            f"ch{i + 1}" for i in range(self._config.n_channels)
        )

        self._seq = 0
        self._sample_index = 0
        self._markers: list[MarkerEvent] = []

        self._is_recording = False
        self._record_session: Optional[RecordSession] = None
        self._record_buffer: list[np.ndarray] = []

        self._preview_timer = QTimer(self)
        self._preview_timer.timeout.connect(self._on_tick)

        self._connect_timer = QTimer(self)
        self._connect_timer.setSingleShot(True)
        self._connect_timer.timeout.connect(self._finish_connect)

        self._disconnect_timer = QTimer(self)
        self._disconnect_timer.setSingleShot(True)
        self._disconnect_timer.timeout.connect(self._finish_disconnect)

        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._finish_search)
        self._pending_search_method = "Native BLE"

        self._burst_remaining = 0
        self._burst_gain = 1.0

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

    def connect_device(self, config: Optional[ConnectConfig] = None) -> None:
        if self._state not in {DeviceState.DISCONNECTED, DeviceState.ERROR}:
            return

        if config is not None:
            self._config = config

        if self._config.n_channels <= 0:
            self._emit_error(
                code="INVALID_CONFIG",
                message="n_channels 必须大于 0",
                detail=f"got n_channels={self._config.n_channels}",
            )
            return

        if self._config.fs <= 0:
            self._emit_error(
                code="INVALID_CONFIG",
                message="fs 必须大于 0",
                detail=f"got fs={self._config.fs}",
            )
            return

        if self._config.chunk_size <= 0:
            self._emit_error(
                code="INVALID_CONFIG",
                message="chunk_size 必须大于 0",
                detail=f"got chunk_size={self._config.chunk_size}",
            )
            return

        self._device_name = self._config.device_name
        self._device_address = self._config.device_address
        self._channel_names = tuple(f"ch{i + 1}" for i in range(self._config.n_channels))
        self._set_state(DeviceState.CONNECTING, "正在连接 mock 设备...")
        self._connect_timer.start(self._config.connect_delay_ms)

    def search_devices(self, method: str) -> None:
        self._pending_search_method = method
        self.sig_search.emit(
            SearchEvent(
                method=method,
                is_searching=True,
                ts=time.time(),
                message="正在搜索设备...",
            )
        )
        self._search_timer.start(1400)

    def load_labels(self) -> None:
        self._labels = self._read_labels_from_disk()
        self._emit_labels("标签已加载")

    def add_label(self, label: str) -> None:
        normalized = label.strip()
        if not normalized:
            return

        if normalized in self._labels:
            self._emit_labels("标签已存在")
            return

        self._labels.append(normalized)
        self._write_labels_to_disk()
        self._emit_labels("标签已添加")

    def remove_label(self, label: str) -> None:
        normalized = label.strip()
        if normalized not in self._labels:
            return

        self._labels.remove(normalized)
        self._write_labels_to_disk()
        self._emit_labels("标签已删除")

    def disconnect_device(self) -> None:
        if self._state not in {
            DeviceState.CONNECTED,
            DeviceState.PREVIEWING,
            DeviceState.RECORDING,
        }:
            return

        if self._is_recording:
            self.stop_record()

        self._preview_timer.stop()
        self._connect_timer.stop()
        self._disconnect_timer.start(900)
        self._set_state(DeviceState.DISCONNECTING, "正在断开设备...")

    def start_preview(self) -> None:
        if self._state != DeviceState.CONNECTED:
            return

        interval_ms = max(1, int(round(1000 * self._config.chunk_size / self._config.fs)))
        self._preview_timer.start(interval_ms)
        self._set_state(DeviceState.PREVIEWING, "开始预览")

    def stop_preview(self) -> None:
        if self._state not in {DeviceState.PREVIEWING, DeviceState.RECORDING}:
            return

        if self._is_recording:
            self.stop_record()

        self._preview_timer.stop()
        self._set_state(DeviceState.CONNECTED, "停止预览")

    def start_record(self, session: Optional[RecordSession] = None) -> None:
        if self._state != DeviceState.PREVIEWING:
            return

        if session is None:
            session = RecordSession(
                session_id=time.strftime("%Y%m%d_%H%M%S"),
                save_dir="./mock_data",
            )

        self._record_session = session
        self._record_buffer.clear()
        self._markers.clear()
        self._is_recording = True

        Path(session.save_dir).mkdir(parents=True, exist_ok=True)
        self.sig_record.emit(
            RecordEvent(
                is_recording=True,
                ts=time.time(),
                session_id=session.session_id,
                save_dir=session.save_dir,
            )
        )
        self._set_state(DeviceState.RECORDING, "开始录制")

    def stop_record(self) -> None:
        if not self._is_recording:
            return

        self._flush_record_to_disk()

        session = self._record_session
        self._is_recording = False
        self._record_session = None
        self._record_buffer.clear()

        self.sig_record.emit(
            RecordEvent(
                is_recording=False,
                ts=time.time(),
                session_id=session.session_id if session else None,
                save_dir=session.save_dir if session else None,
            )
        )

        if self._preview_timer.isActive():
            self._set_state(DeviceState.PREVIEWING, "停止录制")
        else:
            self._set_state(DeviceState.CONNECTED, "停止录制")

    def add_marker(self, label: str, note: str = "", source: str = "ui") -> None:
        if self._state not in {DeviceState.PREVIEWING, DeviceState.RECORDING}:
            return

        event = MarkerEvent(
            marker_id=f"m_{uuid.uuid4().hex[:8]}",
            label=label,
            wall_time=time.time(),
            sample_index=self._sample_index,
            note=note,
            source=source,
        )
        self._markers.append(event)
        self.sig_marker.emit(event)

        if label in {"dry_swallow", "water_5ml", "water_10ml", "water_15ml", "cough"}:
            self._burst_remaining = int(self._config.fs * 0.8)
            self._burst_gain = 2.2 if label != "cough" else 3.2

    def _finish_connect(self) -> None:
        self._reset_stream_runtime()
        self._set_state(DeviceState.CONNECTED, "设备已连接")

    def _finish_disconnect(self) -> None:
        self._reset_stream_runtime()
        self._device_name = "Ganglion Mock"
        self._device_address = ""
        self._set_state(DeviceState.DISCONNECTED, "设备已断开")

    def _finish_search(self) -> None:
        prefix = "BLE" if self._pending_search_method == "Native BLE" else "Dongle"
        results = (
            DeviceSearchResult(
                name=f"Ganglion {prefix} A",
                address="00:11:22:33:44:A1",
                method=self._pending_search_method,
            ),
            DeviceSearchResult(
                name=f"Ganglion {prefix} B",
                address="00:11:22:33:44:B2",
                method=self._pending_search_method,
            ),
        )
        self.sig_search.emit(
            SearchEvent(
                method=self._pending_search_method,
                is_searching=False,
                ts=time.time(),
                results=results,
                message=f"已搜索到 {len(results)} 个设备",
            )
        )

    def _reset_stream_runtime(self) -> None:
        self._seq = 0
        self._sample_index = 0
        self._burst_remaining = 0
        self._burst_gain = 1.0

    def _resolve_labels_path(self) -> Path:
        base_dir = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppDataLocation
        )
        if not base_dir:
            return Path.home() / ".openbciganglionui" / "labels.json"
        return Path(base_dir) / "labels.json"

    def _read_labels_from_disk(self) -> list[str]:
        try:
            if not self._labels_path.exists():
                return ["dry_swallow", "water_5ml", "cough"]
            payload = json.loads(self._labels_path.read_text(encoding="utf-8"))
            labels = payload.get("labels", [])
            return [str(label).strip() for label in labels if str(label).strip()]
        except (OSError, json.JSONDecodeError):
            return ["dry_swallow", "water_5ml", "cough"]

    def _write_labels_to_disk(self) -> None:
        self._labels_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"labels": self._labels}
        self._labels_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _emit_labels(self, message: str = "") -> None:
        self.sig_labels.emit(
            LabelsEvent(
                labels=tuple(self._labels),
                ts=time.time(),
                storage_path=str(self._labels_path),
                message=message,
            )
        )

    def _on_tick(self) -> None:
        try:
            chunk = self._make_chunk()
            if self._is_recording:
                self._record_buffer.append(chunk.data.copy())
            self.sig_stream.emit(chunk)
        except Exception as exc:
            self._preview_timer.stop()
            self._emit_error(
                code="MOCK_STREAM_ERROR",
                message="mock 数据生成失败",
                detail=str(exc),
                recoverable=True,
            )

    def _make_chunk(self) -> StreamChunk:
        fs = float(self._config.fs)
        n_samples = int(self._config.chunk_size)
        n_channels = int(self._config.n_channels)

        t = (np.arange(n_samples, dtype=np.float32) + self._sample_index) / fs
        data = np.zeros((n_samples, n_channels), dtype=np.float32)

        base_freqs = [1.2, 2.5, 0.8, 1.8, 3.2, 0.5, 2.1, 4.0]
        for ch in range(n_channels):
            f0 = base_freqs[ch % len(base_freqs)]
            f1 = f0 * 3.0
            phase = ch * 0.35
            signal = (
                35.0 * np.sin(2.0 * math.pi * f0 * t + phase)
                + 12.0 * np.sin(2.0 * math.pi * f1 * t + 0.2 * ch)
            )
            noise = np.random.normal(0.0, 3.0 + ch * 0.6, size=n_samples)
            drift = 8.0 * np.sin(2.0 * math.pi * 0.08 * t + ch * 0.1)
            data[:, ch] = signal + drift + noise

        if self._burst_remaining > 0:
            burst_n = min(self._burst_remaining, n_samples)
            env = np.linspace(1.0, 0.2, burst_n, dtype=np.float32)
            burst = (
                40.0 * env * np.sin(2.0 * math.pi * 6.0 * t[:burst_n])
            ).reshape(-1, 1)
            data[:burst_n, :] += self._burst_gain * burst
            self._burst_remaining -= n_samples
            if self._burst_remaining <= 0:
                self._burst_gain = 1.0

        chunk = StreamChunk(
            seq=self._seq,
            sample_index0=self._sample_index,
            fs=fs,
            channel_names=self._channel_names,
            data=data,
            received_at=time.time(),
        )

        self._seq += 1
        self._sample_index += n_samples
        return chunk

    def _flush_record_to_disk(self) -> None:
        if not self._record_session or not self._record_buffer:
            return

        session = self._record_session
        save_root = Path(session.save_dir) / session.session_id
        save_root.mkdir(parents=True, exist_ok=True)

        full_data = np.vstack(self._record_buffer)
        timestamps = np.arange(full_data.shape[0], dtype=np.float64) / float(self._config.fs)

        csv_path = save_root / "stream.csv"
        header = "time_sec," + ",".join(self._channel_names)
        np.savetxt(
            csv_path,
            np.column_stack([timestamps, full_data]),
            delimiter=",",
            header=header,
            comments="",
            fmt="%.6f",
        )

        marker_path = save_root / "markers.csv"
        with marker_path.open("w", encoding="utf-8") as file:
            file.write("marker_id,label,wall_time,sample_index,note,source\n")
            for marker in self._markers:
                note = marker.note.replace(",", " ")
                file.write(
                    f"{marker.marker_id},{marker.label},{marker.wall_time:.6f},"
                    f"{marker.sample_index},{note},{marker.source}\n"
                )

        meta_path = save_root / "session_meta.txt"
        with meta_path.open("w", encoding="utf-8") as file:
            file.write(f"session_id={session.session_id}\n")
            file.write(f"subject_id={session.subject_id}\n")
            file.write(f"task_name={session.task_name}\n")
            file.write(f"operator={session.operator}\n")
            file.write(f"notes={session.notes}\n")
            file.write(f"fs={self._config.fs}\n")
            file.write(f"n_channels={self._config.n_channels}\n")
            file.write(f"channel_names={','.join(self._channel_names)}\n")

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
