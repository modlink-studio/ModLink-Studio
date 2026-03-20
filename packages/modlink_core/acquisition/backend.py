from __future__ import annotations

import time
from pathlib import Path

from PyQt6.QtCore import QObject, QThread, Qt, pyqtSignal, pyqtSlot

from packages.modlink_shared import FrameEnvelope, StreamDescriptor

from ..bus import FrameSubscription, StreamBus
from ..settings.service import SettingsService
from .storage import RecordingStorage, clone_descriptor_snapshot

ACQUISITION_ROOT_DIR_KEY = "acquisition.storage.root_dir"


class AcquisitionWorker(QObject):
    sig_error = pyqtSignal(str)
    sig_event = pyqtSignal(object)
    sig_state_changed = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self._state = "idle"
        self._storage: RecordingStorage | None = None
        self._ignored_unknown_streams: set[str] = set()

    @pyqtSlot(object)
    def on_frame(self, frame: object) -> None:
        if not isinstance(frame, FrameEnvelope):
            self.sig_error.emit(
                f"ACQ_INVALID_FRAME: expected FrameEnvelope, got {type(frame).__name__}"
            )
            return
        if self._storage is None:
            return

        try:
            accepted = self._storage.append_frame(frame)
        except Exception as exc:
            self.sig_error.emit(
                f"ACQ_WRITE_FAILED: stream_id={frame.stream_id}: {type(exc).__name__}: {exc}"
            )
            return

        if accepted:
            return

        if frame.stream_id not in self._ignored_unknown_streams:
            self._ignored_unknown_streams.add(frame.stream_id)
            self.sig_error.emit(
                f"ACQ_UNKNOWN_STREAM_DROPPED: stream_id={frame.stream_id}"
            )

    @pyqtSlot(str, str, object, object)
    def start_recording(
        self,
        root_dir: str,
        session_name: str,
        recording_label: object,
        descriptor_snapshot: object,
    ) -> None:
        if self._storage is not None:
            self.sig_error.emit("ACQ_ALREADY_RECORDING")
            return

        if not session_name.strip():
            self.sig_error.emit("ACQ_INVALID_SESSION_NAME")
            return

        if not isinstance(descriptor_snapshot, dict) or not all(
            isinstance(value, StreamDescriptor)
            for value in descriptor_snapshot.values()
        ):
            self.sig_error.emit("ACQ_INVALID_DESCRIPTOR_SNAPSHOT")
            return

        started_at_ns = time.time_ns()
        try:
            self._storage = RecordingStorage(
                Path(root_dir),
                session_name=session_name,
                recording_label=_normalize_optional_text(recording_label),
                descriptor_snapshot=descriptor_snapshot,
                started_at_ns=started_at_ns,
            )
        except Exception as exc:
            self._storage = None
            self.sig_error.emit(f"ACQ_START_FAILED: {type(exc).__name__}: {exc}")
            return

        self._ignored_unknown_streams.clear()
        self._set_state("recording")
        self.sig_event.emit(
            {
                "kind": "recording_started",
                "session_name": session_name,
                "recording_id": self._storage.recording_id,
                "recording_path": str(self._storage.recording_dir),
                "recording_label": _normalize_optional_text(recording_label),
                "ts_ns": started_at_ns,
            }
        )

    @pyqtSlot()
    def stop_recording(self) -> None:
        if self._storage is None:
            self.sig_error.emit("ACQ_STOP_IGNORED: not recording")
            return

        stopped_at_ns = time.time_ns()
        storage = self._storage
        self._storage = None

        try:
            storage.finalize(stopped_at_ns=stopped_at_ns)
        except Exception as exc:
            self.sig_error.emit(f"ACQ_STOP_FAILED: {type(exc).__name__}: {exc}")
        finally:
            self._ignored_unknown_streams.clear()
            self._set_state("idle")

        self.sig_event.emit(
            {
                "kind": "recording_stopped",
                "session_name": storage.session_name,
                "recording_id": storage.recording_id,
                "recording_path": str(storage.recording_dir),
                "frame_counts_by_stream": storage.frame_counts_by_stream,
                "ts_ns": stopped_at_ns,
            }
        )

    @pyqtSlot(object)
    def add_marker(self, label: object) -> None:
        if self._storage is None:
            self.sig_error.emit("ACQ_MARKER_REJECTED: not recording")
            return

        timestamp_ns = time.time_ns()
        normalized_label = _normalize_optional_text(label)
        try:
            self._storage.add_marker(timestamp_ns=timestamp_ns, label=normalized_label)
        except Exception as exc:
            self.sig_error.emit(f"ACQ_MARKER_FAILED: {type(exc).__name__}: {exc}")
            return

        self.sig_event.emit(
            {
                "kind": "marker_added",
                "session_name": self._storage.session_name,
                "recording_id": self._storage.recording_id,
                "timestamp_ns": timestamp_ns,
                "label": normalized_label,
            }
        )

    @pyqtSlot(object, object, object)
    def add_segment(self, start_ns: object, end_ns: object, label: object) -> None:
        if self._storage is None:
            self.sig_error.emit("ACQ_SEGMENT_REJECTED: not recording")
            return

        try:
            start_value = int(start_ns)
            end_value = int(end_ns)
        except (TypeError, ValueError):
            self.sig_error.emit("ACQ_INVALID_SEGMENT_RANGE")
            return

        if start_value > end_value:
            self.sig_error.emit("ACQ_INVALID_SEGMENT_RANGE: start_ns > end_ns")
            return

        normalized_label = _normalize_optional_text(label)
        try:
            self._storage.add_segment(
                start_ns=start_value,
                end_ns=end_value,
                label=normalized_label,
            )
        except Exception as exc:
            self.sig_error.emit(f"ACQ_SEGMENT_FAILED: {type(exc).__name__}: {exc}")
            return

        self.sig_event.emit(
            {
                "kind": "segment_added",
                "session_name": self._storage.session_name,
                "recording_id": self._storage.recording_id,
                "start_ns": start_value,
                "end_ns": end_value,
                "label": normalized_label,
            }
        )

    @pyqtSlot()
    def shutdown(self) -> None:
        if self._storage is not None:
            self.stop_recording()

    def _set_state(self, state: str) -> None:
        if state == self._state:
            return
        self._state = state
        self.sig_state_changed.emit(state)


class AcquisitionBackend(QObject):
    """Threaded acquisition backend that records bus frames to disk."""

    sig_error = pyqtSignal(str)
    sig_event = pyqtSignal(object)
    sig_state_changed = pyqtSignal(str)

    _request_start_recording = pyqtSignal(str, str, object, object)
    _request_stop_recording = pyqtSignal()
    _request_add_marker = pyqtSignal(object)
    _request_add_segment = pyqtSignal(object, object, object)
    _request_shutdown = pyqtSignal()

    def __init__(
        self,
        bus: StreamBus,
        *,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self._bus = bus
        self._settings = SettingsService.instance()
        self._thread = QThread(self)
        self._thread.setObjectName("modlink.acquisition")
        self._worker = AcquisitionWorker()
        self._frame_subscription: FrameSubscription | None = None
        self._state = "idle"
        self._started = False

        self._worker.moveToThread(self._thread)

        self._request_start_recording.connect(
            self._worker.start_recording,
            Qt.ConnectionType.QueuedConnection,
        )
        self._request_stop_recording.connect(
            self._worker.stop_recording,
            Qt.ConnectionType.QueuedConnection,
        )
        self._request_add_marker.connect(
            self._worker.add_marker,
            Qt.ConnectionType.QueuedConnection,
        )
        self._request_add_segment.connect(
            self._worker.add_segment,
            Qt.ConnectionType.QueuedConnection,
        )
        self._request_shutdown.connect(
            self._worker.shutdown,
            Qt.ConnectionType.QueuedConnection,
        )

        self._worker.sig_error.connect(self.sig_error.emit)
        self._worker.sig_event.connect(self.sig_event.emit)
        self._worker.sig_state_changed.connect(self._on_state_changed)

    @property
    def root_dir(self) -> Path:
        return _resolve_root_dir(self._settings)

    @property
    def is_started(self) -> bool:
        return self._started and self._thread.isRunning()

    def start(self) -> None:
        if self._thread.isRunning():
            self._started = True
            return
        self._frame_subscription = self._bus.subscribe(
            self._worker.on_frame,
            connection_type=Qt.ConnectionType.QueuedConnection,
        )
        self._thread.start()
        self._started = True

    @property
    def state(self) -> str:
        return self._state

    @property
    def is_recording(self) -> bool:
        return self._state == "recording"

    def start_recording(
        self,
        session_name: str,
        recording_label: str | None = None,
    ) -> None:
        if not self._thread.isRunning():
            self.sig_error.emit("ACQ_NOT_STARTED")
            return
        descriptor_snapshot = clone_descriptor_snapshot(self._bus.descriptors())
        root_dir = _resolve_root_dir(self._settings)
        self._request_start_recording.emit(
            str(root_dir),
            session_name,
            recording_label,
            descriptor_snapshot,
        )

    def stop_recording(self) -> None:
        if not self._thread.isRunning():
            self.sig_error.emit("ACQ_NOT_STARTED")
            return
        self._request_stop_recording.emit()

    def add_marker(self, label: str | None = None) -> None:
        if not self._thread.isRunning():
            self.sig_error.emit("ACQ_NOT_STARTED")
            return
        self._request_add_marker.emit(label)

    def add_segment(
        self,
        start_ns: int,
        end_ns: int,
        label: str | None = None,
    ) -> None:
        if not self._thread.isRunning():
            self.sig_error.emit("ACQ_NOT_STARTED")
            return
        self._request_add_segment.emit(start_ns, end_ns, label)

    def shutdown(self, *, timeout_ms: int = 3000) -> None:
        if self._frame_subscription is not None:
            self._frame_subscription.close()
            self._frame_subscription = None

        if not self._thread.isRunning():
            self._state = "idle"
            self._started = False
            return

        self._request_shutdown.emit()
        self._thread.quit()
        if not self._thread.wait(timeout_ms):
            self.sig_error.emit(f"ACQ_STOP_TIMEOUT: timeout_ms={timeout_ms}")
        self._state = "idle"
        self._started = False

    @pyqtSlot(str)
    def _on_state_changed(self, state: str) -> None:
        self._state = state
        self.sig_state_changed.emit(state)


def _normalize_optional_text(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _default_root_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "data"


def _resolve_root_dir(settings: SettingsService) -> Path:
    root_dir = settings.get(ACQUISITION_ROOT_DIR_KEY)
    if root_dir is None:
        resolved_root_dir = _default_root_dir()
        settings.set(ACQUISITION_ROOT_DIR_KEY, str(resolved_root_dir), persist=False)
        return resolved_root_dir
    return Path(root_dir)
