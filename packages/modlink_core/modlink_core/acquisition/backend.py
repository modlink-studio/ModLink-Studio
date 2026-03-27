from __future__ import annotations

import queue
import threading
import time
from pathlib import Path

from platformdirs import user_documents_path

from modlink_sdk import FrameEnvelope, StreamDescriptor
from modlink_sdk.signals import Signal

from ..bus import FrameSubscription, StreamBus
from ..settings.service import SettingsService
from .storage import RecordingStorage

ACQUISITION_ROOT_DIR_KEY = "acquisition.storage.root_dir"


class AcquisitionBackend:
    """Threaded acquisition backend that records bus frames to disk."""

    def __init__(
        self,
        bus: StreamBus,
        *,
        parent: object | None = None,
    ) -> None:
        self.sig_error = Signal()
        self.sig_event = Signal()
        self.sig_state_changed = Signal()
        self._bus = bus
        self._parent = parent
        self._settings = SettingsService.instance()
        self._command_queue: queue.Queue[tuple[str, object | None]] = queue.Queue()
        self._thread: threading.Thread | None = None
        self._frame_subscription: FrameSubscription | None = None
        self._state = "idle"
        self._started = False
        self._storage: RecordingStorage | None = None
        self._lock = threading.RLock()

    @property
    def root_dir(self) -> Path:
        return _resolve_root_dir(self._settings)

    @property
    def is_started(self) -> bool:
        thread = self._thread
        return self._started and thread is not None and thread.is_alive()

    @property
    def state(self) -> str:
        return self._state

    @property
    def is_recording(self) -> bool:
        return self._state == "recording"

    def start(self) -> None:
        if self.is_started:
            self._started = True
            return
        self._frame_subscription = self._bus.subscribe(self._on_frame)
        thread = threading.Thread(
            target=self._run,
            name="modlink.acquisition",
            daemon=True,
        )
        self._thread = thread
        self._started = True
        thread.start()

    def start_recording(
        self,
        session_name: str,
        recording_label: str | None = None,
    ) -> None:
        if not self.is_started:
            self.sig_error.emit("ACQ_NOT_STARTED")
            return
        self._command_queue.put(
            (
                "start_recording",
                (
                    str(_resolve_root_dir(self._settings)),
                    session_name,
                    recording_label,
                    self._bus.descriptors(),
                ),
            )
        )

    def stop_recording(self) -> None:
        if not self.is_started:
            self.sig_error.emit("ACQ_NOT_STARTED")
            return
        self._command_queue.put(("stop_recording", None))

    def add_marker(self, label: str | None = None) -> None:
        if not self.is_started:
            self.sig_error.emit("ACQ_NOT_STARTED")
            return
        self._command_queue.put(("add_marker", label))

    def add_segment(
        self,
        start_ns: int,
        end_ns: int,
        label: str | None = None,
    ) -> None:
        if not self.is_started:
            self.sig_error.emit("ACQ_NOT_STARTED")
            return
        self._command_queue.put(("add_segment", (start_ns, end_ns, label)))

    def shutdown(self, *, timeout_ms: int = 3000) -> None:
        if self._frame_subscription is not None:
            self._frame_subscription.close()
            self._frame_subscription = None

        thread = self._thread
        if thread is None or not thread.is_alive():
            self._state = "idle"
            self._started = False
            return

        self._command_queue.put(("shutdown", None))
        thread.join(max(0, timeout_ms) / 1000)
        if thread.is_alive():
            self.sig_error.emit(f"ACQ_STOP_TIMEOUT: timeout_ms={timeout_ms}")

        self._state = "idle"
        self._started = False
        self._thread = None

    def _run(self) -> None:
        while True:
            action, payload = self._command_queue.get()
            if action == "shutdown":
                self._shutdown_worker()
                return
            if action == "frame":
                self._on_frame_worker(payload)
                continue
            if action == "start_recording":
                root_dir, session_name, recording_label, recording_descriptors = payload
                self._start_recording_worker(
                    str(root_dir),
                    str(session_name),
                    recording_label,
                    recording_descriptors,
                )
                continue
            if action == "stop_recording":
                self._stop_recording_worker()
                continue
            if action == "add_marker":
                self._add_marker_worker(payload)
                continue
            if action == "add_segment":
                start_ns, end_ns, label = payload
                self._add_segment_worker(start_ns, end_ns, label)

    def _on_frame(self, frame: FrameEnvelope) -> None:
        if not self.is_started:
            return
        self._command_queue.put(("frame", frame))

    def _on_frame_worker(self, frame: object) -> None:
        if not isinstance(frame, FrameEnvelope):
            self.sig_error.emit(
                f"ACQ_INVALID_FRAME: expected FrameEnvelope, got {type(frame).__name__}"
            )
            return
        if self._storage is None:
            return

        try:
            self._storage.append_frame(frame)
        except Exception as exc:
            self.sig_error.emit(
                f"ACQ_WRITE_FAILED: stream_id={frame.stream_id}: {type(exc).__name__}: {exc}"
            )

    def _start_recording_worker(
        self,
        root_dir: str,
        session_name: str,
        recording_label: object,
        recording_descriptors: object,
    ) -> None:
        if self._storage is not None:
            self.sig_error.emit("ACQ_ALREADY_RECORDING")
            return

        if not session_name.strip():
            self.sig_error.emit("ACQ_INVALID_SESSION_NAME")
            return

        if not isinstance(recording_descriptors, dict) or not all(
            isinstance(value, StreamDescriptor)
            for value in recording_descriptors.values()
        ):
            self.sig_error.emit("ACQ_INVALID_DESCRIPTOR_SNAPSHOT")
            return

        started_at_ns = time.time_ns()
        try:
            self._storage = RecordingStorage(
                Path(root_dir),
                session_name=session_name,
                recording_label=recording_label or None,
                recording_descriptors=recording_descriptors,
                started_at_ns=started_at_ns,
            )
        except Exception as exc:
            self._storage = None
            self.sig_error.emit(f"ACQ_START_FAILED: {type(exc).__name__}: {exc}")
            return

        self._set_state("recording")
        self.sig_event.emit(
            {
                "kind": "recording_started",
                "session_name": session_name,
                "recording_id": self._storage.recording_id,
                "recording_path": str(self._storage.recording_dir),
                "recording_label": recording_label or None,
                "ts_ns": started_at_ns,
            }
        )

    def _stop_recording_worker(self) -> None:
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

    def _add_marker_worker(self, label: object) -> None:
        if self._storage is None:
            self.sig_error.emit("ACQ_MARKER_REJECTED: not recording")
            return

        timestamp_ns = time.time_ns()
        normalized_label = label or None
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

    def _add_segment_worker(
        self,
        start_ns: object,
        end_ns: object,
        label: object,
    ) -> None:
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

        normalized_label = label or None
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

    def _shutdown_worker(self) -> None:
        if self._storage is not None:
            self._stop_recording_worker()

    def _set_state(self, state: str) -> None:
        with self._lock:
            if state == self._state:
                return
            self._state = state
        self.sig_state_changed.emit(state)


def _default_root_dir() -> Path:
    documents_dir = user_documents_path()
    if documents_dir:
        return Path(documents_dir) / "ModLink Studio" / "data"
    return Path.home() / "ModLink Studio" / "data"


def _resolve_root_dir(settings: SettingsService) -> Path:
    root_dir = settings.get(ACQUISITION_ROOT_DIR_KEY)
    if root_dir is None:
        resolved_root_dir = _default_root_dir()
        settings.set(ACQUISITION_ROOT_DIR_KEY, str(resolved_root_dir), persist=False)
        return resolved_root_dir
    return Path(root_dir)
