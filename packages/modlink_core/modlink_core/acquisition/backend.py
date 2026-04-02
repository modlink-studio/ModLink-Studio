from __future__ import annotations

from collections.abc import Callable
import queue
import threading
import time
from pathlib import Path

from platformdirs import user_documents_path

from modlink_sdk import FrameEnvelope, StreamDescriptor

from ..bus import FrameStream, FrameStreamOverflowError, StreamBus
from ..events import (
    AcquisitionErrorEvent,
    AcquisitionLifecycleEvent,
    AcquisitionSnapshot,
    AcquisitionStateChangedEvent,
    BackendEvent,
    StreamClosedError,
)
from ..settings.service import SettingsService
from .storage import RecordingStorage

ACQUISITION_ROOT_DIR_KEY = "acquisition.storage.root_dir"
ACQUISITION_CONSUMER_NAME = "acquisition"


class AcquisitionBackend:
    """Threaded acquisition backend that records bus frames to disk."""

    def __init__(
        self,
        bus: StreamBus,
        *,
        settings: SettingsService,
        publish_event: Callable[[BackendEvent], None],
        parent: object | None = None,
    ) -> None:
        self._bus = bus
        self._settings = settings
        self._publish_event = publish_event
        self._parent = parent
        self._command_queue: queue.Queue[tuple[str, object | None]] = queue.Queue()
        self._thread: threading.Thread | None = None
        self._frame_stream: FrameStream | None = None
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

    def snapshot(self) -> AcquisitionSnapshot:
        return AcquisitionSnapshot(
            state=self._state,
            is_started=self.is_started,
            is_recording=self.is_recording,
            root_dir=str(self.root_dir),
        )

    def start(self) -> None:
        if self.is_started:
            self._started = True
            return
        if self._frame_stream is None or self._frame_stream.closed:
            self._frame_stream = self._open_frame_stream()
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
            self._publish_error("ACQ_NOT_STARTED")
            return
        self._command_queue.put(
            (
                "start_recording",
                (
                    str(self.root_dir),
                    session_name,
                    recording_label,
                    self._bus.descriptors(),
                ),
            )
        )

    def stop_recording(self) -> None:
        if not self.is_started:
            self._publish_error("ACQ_NOT_STARTED")
            return
        self._command_queue.put(("stop_recording", None))

    def add_marker(self, label: str | None = None) -> None:
        if not self.is_started:
            self._publish_error("ACQ_NOT_STARTED")
            return
        self._command_queue.put(("add_marker", label))

    def add_segment(
        self,
        start_ns: int,
        end_ns: int,
        label: str | None = None,
    ) -> None:
        if not self.is_started:
            self._publish_error("ACQ_NOT_STARTED")
            return
        self._command_queue.put(("add_segment", (start_ns, end_ns, label)))

    def shutdown(self, *, timeout_ms: int = 3000) -> None:
        thread = self._thread
        if thread is None or not thread.is_alive():
            self._set_state("idle")
            self._started = False
            if self._frame_stream is not None:
                self._frame_stream.close()
                self._frame_stream = None
            return

        self._command_queue.put(("shutdown", None))
        thread.join(max(0, timeout_ms) / 1000)
        if thread.is_alive():
            self._publish_error(f"ACQ_STOP_TIMEOUT: timeout_ms={timeout_ms}")

        self._set_state("idle")
        self._started = False
        self._thread = None
        if self._frame_stream is not None:
            self._frame_stream.close()
            self._frame_stream = None

    def _run(self) -> None:
        while True:
            if self._drain_commands():
                return

            frame_stream = self._frame_stream
            if frame_stream is None:
                time.sleep(0.01)
                continue

            try:
                frame = frame_stream.read(timeout=0.05)
            except queue.Empty:
                continue
            except StreamClosedError:
                if not self._started:
                    return
                self._frame_stream = self._open_frame_stream()
                continue
            except FrameStreamOverflowError as exc:
                self._handle_frame_stream_overflow(exc.consumer_name)
                continue

            if not self.is_recording:
                continue
            self._on_frame_worker(frame)

    def _drain_commands(self) -> bool:
        while True:
            try:
                action, payload = self._command_queue.get_nowait()
            except queue.Empty:
                return False

            if action == "shutdown":
                self._shutdown_worker()
                return True
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

    def _on_frame_worker(self, frame: object) -> None:
        if not isinstance(frame, FrameEnvelope):
            self._publish_error(
                f"ACQ_INVALID_FRAME: expected FrameEnvelope, got {type(frame).__name__}"
            )
            return
        if self._storage is None:
            return

        try:
            self._storage.append_frame(frame)
        except Exception as exc:
            self._publish_error(
                f"ACQ_WRITE_FAILED: stream_id={frame.stream_id}: {type(exc).__name__}: {exc}"
            )
            self._fail_recording_worker("write_failed")

    def _start_recording_worker(
        self,
        root_dir: str,
        session_name: str,
        recording_label: object,
        recording_descriptors: object,
    ) -> None:
        if self._storage is not None:
            self._publish_error("ACQ_ALREADY_RECORDING")
            return

        if not session_name.strip():
            self._publish_error("ACQ_INVALID_SESSION_NAME")
            return

        if not isinstance(recording_descriptors, dict) or not all(
            isinstance(value, StreamDescriptor)
            for value in recording_descriptors.values()
        ):
            self._publish_error("ACQ_INVALID_DESCRIPTOR_SNAPSHOT")
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
            self._publish_error(f"ACQ_START_FAILED: {type(exc).__name__}: {exc}")
            return

        self._set_state("recording")
        self._publish_event(
            AcquisitionLifecycleEvent(
                name="recording_started",
                payload={
                    "session_name": session_name,
                    "recording_id": self._storage.recording_id,
                    "recording_path": str(self._storage.recording_dir),
                    "recording_label": recording_label or None,
                    "ts_ns": started_at_ns,
                },
            )
        )

    def _stop_recording_worker(self) -> None:
        if self._storage is None:
            self._publish_error("ACQ_STOP_IGNORED: not recording")
            return

        stopped_at_ns = time.time_ns()
        storage = self._storage
        self._storage = None

        failure_reason = self._finalize_recording_storage(
            storage,
            stopped_at_ns=stopped_at_ns,
            status="completed",
        )
        self._set_state("idle")
        if failure_reason is not None:
            self._publish_recording_failed(
                storage,
                stopped_at_ns=stopped_at_ns,
                reason=failure_reason,
            )
            return

        self._publish_event(
            AcquisitionLifecycleEvent(
                name="recording_stopped",
                payload={
                    "session_name": storage.session_name,
                    "recording_id": storage.recording_id,
                    "recording_path": str(storage.recording_dir),
                    "frame_counts_by_stream": storage.frame_counts_by_stream,
                    "ts_ns": stopped_at_ns,
                },
            )
        )

    def _add_marker_worker(self, label: object) -> None:
        if self._storage is None:
            self._publish_error("ACQ_MARKER_REJECTED: not recording")
            return

        timestamp_ns = time.time_ns()
        normalized_label = label or None
        try:
            self._storage.add_marker(timestamp_ns=timestamp_ns, label=normalized_label)
        except Exception as exc:
            self._publish_error(f"ACQ_MARKER_FAILED: {type(exc).__name__}: {exc}")
            return

        self._publish_event(
            AcquisitionLifecycleEvent(
                name="marker_added",
                payload={
                    "session_name": self._storage.session_name,
                    "recording_id": self._storage.recording_id,
                    "timestamp_ns": timestamp_ns,
                    "label": normalized_label,
                },
            )
        )

    def _add_segment_worker(
        self,
        start_ns: object,
        end_ns: object,
        label: object,
    ) -> None:
        if self._storage is None:
            self._publish_error("ACQ_SEGMENT_REJECTED: not recording")
            return

        try:
            start_value = int(start_ns)
            end_value = int(end_ns)
        except (TypeError, ValueError):
            self._publish_error("ACQ_INVALID_SEGMENT_RANGE")
            return

        if start_value > end_value:
            self._publish_error("ACQ_INVALID_SEGMENT_RANGE: start_ns > end_ns")
            return

        normalized_label = label or None
        try:
            self._storage.add_segment(
                start_ns=start_value,
                end_ns=end_value,
                label=normalized_label,
            )
        except Exception as exc:
            self._publish_error(f"ACQ_SEGMENT_FAILED: {type(exc).__name__}: {exc}")
            return

        self._publish_event(
            AcquisitionLifecycleEvent(
                name="segment_added",
                payload={
                    "session_name": self._storage.session_name,
                    "recording_id": self._storage.recording_id,
                    "start_ns": start_value,
                    "end_ns": end_value,
                    "label": normalized_label,
                },
            )
        )

    def _handle_frame_stream_overflow(self, consumer_name: str) -> None:
        self._publish_error(f"ACQ_FRAME_STREAM_OVERFLOW: {consumer_name}")
        if self._storage is not None:
            self._fail_recording_worker("frame_stream_overflow")
        self._replace_frame_stream()

    def _replace_frame_stream(self) -> None:
        previous_stream = self._frame_stream
        self._frame_stream = self._open_frame_stream()
        if previous_stream is not None:
            previous_stream.close()

    def _open_frame_stream(self) -> FrameStream:
        return self._bus.open_frame_stream(
            maxsize=256,
            drop_policy="error",
            consumer_name=ACQUISITION_CONSUMER_NAME,
        )

    def _shutdown_worker(self) -> None:
        if self._storage is not None:
            self._stop_recording_worker()

    def _fail_recording_worker(self, reason: str) -> None:
        storage = self._storage
        if storage is None:
            return

        stopped_at_ns = time.time_ns()
        self._storage = None
        final_reason = self._finalize_recording_storage(
            storage,
            stopped_at_ns=stopped_at_ns,
            status="failed",
        )
        self._set_state("idle")
        self._publish_recording_failed(
            storage,
            stopped_at_ns=stopped_at_ns,
            reason=final_reason or reason,
        )

    def _finalize_recording_storage(
        self,
        storage: RecordingStorage,
        *,
        stopped_at_ns: int,
        status: str,
    ) -> str | None:
        try:
            storage.finalize(stopped_at_ns=stopped_at_ns, status=status)
            return None
        except Exception as exc:
            self._publish_error(f"ACQ_FINALIZE_FAILED: {type(exc).__name__}: {exc}")
            try:
                storage.write_manifest(stopped_at_ns=stopped_at_ns, status="failed")
            except Exception:
                pass
            return "finalize_failed"

    def _publish_recording_failed(
        self,
        storage: RecordingStorage,
        *,
        stopped_at_ns: int,
        reason: str,
    ) -> None:
        self._publish_event(
            AcquisitionLifecycleEvent(
                name="recording_failed",
                payload={
                    "session_name": storage.session_name,
                    "recording_id": storage.recording_id,
                    "recording_path": str(storage.recording_dir),
                    "frame_counts_by_stream": storage.frame_counts_by_stream,
                    "reason": reason,
                    "ts_ns": stopped_at_ns,
                },
            )
        )

    def _set_state(self, state: str) -> None:
        with self._lock:
            if state == self._state:
                return
            self._state = state
        self._publish_event(AcquisitionStateChangedEvent(snapshot=self.snapshot()))

    def _publish_error(self, message: str) -> None:
        self._publish_event(AcquisitionErrorEvent(message=message))


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
