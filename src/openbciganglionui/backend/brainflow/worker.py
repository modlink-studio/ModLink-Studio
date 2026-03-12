from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np
from PyQt6.QtCore import QObject, QTimer, pyqtSignal, pyqtSlot

from ..models import ConnectConfig

try:
    from brainflow.board_shim import BoardIds, BoardShim, BrainFlowInputParams
except Exception as exc:  # pragma: no cover - depends on local env
    BoardIds = None
    BoardShim = None
    BrainFlowInputParams = None
    _BRAINFLOW_IMPORT_ERROR = exc
else:
    _BRAINFLOW_IMPORT_ERROR = None


NATIVE_BLE_METHOD = "Native BLE"
DONGLE_METHOD = "Ganglion Dongle"


@dataclass(slots=True)
class WorkerConnectionInfo:
    board_id: int
    fs: float
    channel_names: tuple[str, ...]
    device_name: str
    device_address: str


@dataclass(slots=True)
class WorkerChunk:
    data: np.ndarray
    received_at: float


@dataclass(slots=True)
class WorkerFailure:
    code: str
    message: str
    detail: str = ""
    recoverable: bool = True
    transition_to_error: bool = True


@dataclass(slots=True)
class ConnectionAttempt:
    board_id: int
    params: BrainFlowInputParams
    description: str
    display_address: str


class BrainFlowWorker(QObject):
    sig_connected = pyqtSignal(object)
    sig_disconnected = pyqtSignal()
    sig_preview_started = pyqtSignal()
    sig_preview_stopped = pyqtSignal()
    sig_stream = pyqtSignal(object)
    sig_error = pyqtSignal(object)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent=parent)
        self._board = None
        self._board_id = 0
        self._connection_method = ""
        self._eeg_channels: tuple[int, ...] = ()
        self._channel_names: tuple[str, ...] = ()
        self._fs = 0.0
        self._stream_active = False

        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_stream)

    @pyqtSlot(object)
    def connect_device(self, config: ConnectConfig) -> None:
        attempt_errors: list[str] = []
        try:
            self._require_brainflow()
            self._teardown_session()

            for attempt in self._build_connection_attempts(config):
                board = None
                try:
                    board = BoardShim(attempt.board_id, attempt.params)
                    board.prepare_session()

                    self._board = board
                    self._board_id = int(attempt.board_id)
                    self._connection_method = str(config.connection_method).strip()
                    self._eeg_channels = tuple(
                        int(index) for index in BoardShim.get_eeg_channels(attempt.board_id)
                    )
                    self._fs = float(BoardShim.get_sampling_rate(attempt.board_id))
                    self._channel_names = self._resolve_channel_names(
                        attempt.board_id,
                        len(self._eeg_channels),
                    )
                    self._stream_active = False

                    self.sig_connected.emit(
                        WorkerConnectionInfo(
                            board_id=self._board_id,
                            fs=self._fs,
                            channel_names=self._channel_names,
                            device_name=self._resolve_device_name(config),
                            device_address=attempt.display_address or self._resolve_device_address(config),
                        )
                    )
                    return
                except Exception as exc:
                    attempt_errors.append(f"{attempt.description}: {exc}")
                    if board is not None:
                        try:
                            board.release_session()
                        except Exception:
                            pass

            raise RuntimeError(" | ".join(attempt_errors) or "no connection attempts were generated")
        except Exception as exc:
            self._teardown_session()
            self.sig_error.emit(
                WorkerFailure(
                    code="BRAINFLOW_CONNECT_FAILED",
                    message="连接 BrainFlow 设备失败",
                    detail=str(exc),
                    recoverable=True,
                    transition_to_error=True,
                )
            )

    @pyqtSlot(int)
    def start_preview(self, poll_interval_ms: int) -> None:
        if self._board is None:
            self.sig_error.emit(
                WorkerFailure(
                    code="BRAINFLOW_NOT_CONNECTED",
                    message="设备尚未准备完成",
                    detail="prepare_session has not completed",
                    recoverable=True,
                    transition_to_error=True,
                )
            )
            return

        try:
            if not self._stream_active:
                self._board.start_stream(45_000, "")
                self._stream_active = True
            self._poll_timer.start(max(20, int(poll_interval_ms)))
            self.sig_preview_started.emit()
        except Exception as exc:
            self._poll_timer.stop()
            self._stream_active = False
            self.sig_error.emit(
                WorkerFailure(
                    code="BRAINFLOW_START_STREAM_FAILED",
                    message="启动实时流失败",
                    detail=str(exc),
                    recoverable=True,
                    transition_to_error=True,
                )
            )

    @pyqtSlot()
    def stop_preview(self) -> None:
        try:
            self._poll_timer.stop()
            if self._board is not None and self._stream_active:
                self._board.stop_stream()
            self._stream_active = False
            self.sig_preview_stopped.emit()
        except Exception as exc:
            self._poll_timer.stop()
            self._stream_active = False
            self.sig_error.emit(
                WorkerFailure(
                    code="BRAINFLOW_STOP_STREAM_FAILED",
                    message="停止实时流失败",
                    detail=str(exc),
                    recoverable=True,
                    transition_to_error=True,
                )
            )

    @pyqtSlot()
    def disconnect_device(self) -> None:
        try:
            self._teardown_session()
            self.sig_disconnected.emit()
        except Exception as exc:
            self.sig_error.emit(
                WorkerFailure(
                    code="BRAINFLOW_DISCONNECT_FAILED",
                    message="断开设备失败",
                    detail=str(exc),
                    recoverable=True,
                    transition_to_error=False,
                )
            )
            self.sig_disconnected.emit()

    @pyqtSlot(float)
    def insert_marker(self, value: float) -> None:
        if self._board is None or not self._stream_active:
            self.sig_error.emit(
                WorkerFailure(
                    code="BRAINFLOW_MARKER_SKIPPED",
                    message="未能把 marker 写入 BrainFlow 数据流",
                    detail="stream is not active",
                    recoverable=True,
                    transition_to_error=False,
                )
            )
            return

        try:
            self._board.insert_marker(float(value))
        except Exception as exc:
            self.sig_error.emit(
                WorkerFailure(
                    code="BRAINFLOW_MARKER_FAILED",
                    message="写入 BrainFlow marker 失败",
                    detail=str(exc),
                    recoverable=True,
                    transition_to_error=False,
                )
            )

    @pyqtSlot()
    def shutdown(self) -> None:
        self._teardown_session()

    def _poll_stream(self) -> None:
        if self._board is None or not self._stream_active:
            return

        try:
            if int(self._board.get_board_data_count()) <= 0:
                return

            board_data = self._board.get_board_data()
            if board_data is None or getattr(board_data, "size", 0) == 0:
                return

            eeg_rows = board_data[list(self._eeg_channels), :]
            if eeg_rows.size == 0:
                return

            self.sig_stream.emit(
                WorkerChunk(
                    data=np.ascontiguousarray(eeg_rows.T, dtype=np.float32),
                    received_at=time.time(),
                )
            )
        except Exception as exc:
            self._poll_timer.stop()
            self._stream_active = False
            self.sig_error.emit(
                WorkerFailure(
                    code="BRAINFLOW_STREAM_FAILED",
                    message="BrainFlow 流读取失败",
                    detail=str(exc),
                    recoverable=True,
                    transition_to_error=True,
                )
            )

    def _teardown_session(self) -> None:
        self._poll_timer.stop()
        if self._board is not None and self._stream_active:
            try:
                self._board.stop_stream()
            except Exception:
                pass

        if self._board is not None:
            self._disconnect_dongle_session()
            try:
                self._board.release_session()
            except Exception:
                pass

        self._board = None
        self._board_id = 0
        self._connection_method = ""
        self._eeg_channels = ()
        self._channel_names = ()
        self._fs = 0.0
        self._stream_active = False

    def _disconnect_dongle_session(self) -> None:
        if self._board is None:
            return
        if self._connection_method != DONGLE_METHOD:
            return
        if BoardIds is None:
            return
        if self._board_id != int(BoardIds.GANGLION_BOARD.value):
            return

        try:
            # Best-effort radio teardown for the BLED112 dongle path.
            self._board.config_board("v")
        except Exception:
            pass

    def _require_brainflow(self) -> None:
        if BoardShim is None or BrainFlowInputParams is None or BoardIds is None:
            raise RuntimeError("brainflow is not installed") from _BRAINFLOW_IMPORT_ERROR

    def _build_connection_attempts(self, config: ConnectConfig) -> list[ConnectionAttempt]:
        method = str(config.connection_method).strip() or NATIVE_BLE_METHOD
        if method == DONGLE_METHOD:
            params = BrainFlowInputParams()
            params.timeout = int(max(1, config.timeout_sec))
            params.serial_port = (config.serial_port or config.device_address).strip()
            if not params.serial_port:
                raise ValueError("serial_port is required for Ganglion Dongle")
            if config.mac_address.strip():
                params.mac_address = config.mac_address.strip()
            firmware_hint = str(config.firmware_hint).strip().lower() or "auto"
            if firmware_hint in {"auto", "2", "3"}:
                params.other_info = f"fw:{firmware_hint}"
            return [
                ConnectionAttempt(
                    board_id=int(BoardIds.GANGLION_BOARD.value),
                    params=params,
                    description=(
                        f"Ganglion Dongle serial_port={params.serial_port} "
                        f"fw={firmware_hint}"
                    ),
                    display_address=params.serial_port,
                )
            ]

        firmware_hints = self._native_firmware_hints(config.firmware_hint)
        serial_number = config.serial_number.strip()
        if not serial_number:
            raise ValueError("serial_number is required for Native BLE")

        attempts: list[ConnectionAttempt] = []
        for firmware_hint in firmware_hints:
            params = BrainFlowInputParams()
            params.timeout = int(max(1, config.timeout_sec))
            params.other_info = f"fw:{firmware_hint}"
            params.serial_number = serial_number

            description = (
                f"Ganglion Native fw={firmware_hint} "
                f"serial_number={serial_number}"
            )
            attempts.append(
                ConnectionAttempt(
                    board_id=int(BoardIds.GANGLION_NATIVE_BOARD.value),
                    params=params,
                    description=description,
                    display_address=serial_number,
                )
            )

        return attempts

    def _native_firmware_hints(self, firmware_hint: str) -> tuple[str, ...]:
        normalized = str(firmware_hint).strip().lower() or "auto"
        if normalized == "auto":
            return ("auto", "2", "3")
        if normalized in {"2", "3"}:
            return (normalized,)
        return ("auto", "2", "3")

    def _resolve_channel_names(self, board_id: int, n_channels: int) -> tuple[str, ...]:
        descr = BoardShim.get_board_descr(board_id)
        eeg_names = descr.get("eeg_names", "")
        if isinstance(eeg_names, str):
            names = tuple(part.strip() for part in eeg_names.split(",") if part.strip())
            if len(names) >= n_channels:
                return names[:n_channels]
        return tuple(f"ch{index + 1}" for index in range(n_channels))

    def _resolve_device_name(self, config: ConnectConfig) -> str:
        normalized = str(config.device_name).strip()
        if normalized:
            return normalized
        if str(config.connection_method).strip() == DONGLE_METHOD:
            return "Ganglion Dongle"
        return "Ganglion Native BLE"

    def _resolve_device_address(self, config: ConnectConfig) -> str:
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
