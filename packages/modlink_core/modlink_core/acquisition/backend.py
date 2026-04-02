from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import Future
import queue
import threading
import time
from pathlib import Path

from platformdirs import user_documents_path

from modlink_sdk import FrameEnvelope, StreamDescriptor

from ..bus import FrameStream, FrameStreamOverflowError, StreamBus
from ..event_stream import StreamClosedError
from ..events import (
    AcquisitionSnapshot,
    BackendEvent,
    RecordingFailedEvent,
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
        self._command_queue: queue.Queue[
            tuple[str, object | None, Future[None] | None]
        ] = queue.Queue()
        self._thread: threading.Thread | None = None
        self._frame_stream: FrameStream | None = None
        self._state = "idle"
        self._started = False
        self._accepting_commands = False
        self._worker_exit_error: Exception | None = None
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
            self._accepting_commands = True
            return
        if self._frame_stream is None or self._frame_stream.closed:
            self._frame_stream = self._open_frame_stream()
        thread = threading.Thread(
            target=self._run,
            name="modlink.acquisition",
            daemon=True,
        )
        self._thread = thread
        self._worker_exit_error = None
        self._accepting_commands = True
        self._started = True
        thread.start()

    def start_recording(
        self,
        session_name: str,
        recording_label: str | None = None,
    ) -> Future[None]:
        return self._submit_command(
            "start_recording",
            (
                str(self.root_dir),
                session_name,
                recording_label,
                self._bus.descriptors(),
            ),
        )

    def stop_recording(self) -> Future[None]:
        return self._submit_command("stop_recording")

    def add_marker(self, label: str | None = None) -> Future[None]:
        return self._submit_command("add_marker", label)

    def add_segment(
        self,
        start_ns: int,
        end_ns: int,
        label: str | None = None,
    ) -> Future[None]:
        return self._submit_command("add_segment", (start_ns, end_ns, label))

    def shutdown(self, *, timeout_ms: int = 3000) -> None:
        with self._lock:
            self._accepting_commands = False
            thread = self._thread
            worker_exit_error = self._worker_exit_error

        if thread is None or not thread.is_alive():
            self._finalize_shutdown()
            if worker_exit_error is not None:
                self._worker_exit_error = None
                raise worker_exit_error
            return

        self._command_queue.put(("shutdown", None, None))
        thread.join(max(0, timeout_ms) / 1000)

        if thread.is_alive():
            raise TimeoutError(f"acquisition shutdown timed out after {timeout_ms}ms")

        self._finalize_shutdown()
        worker_exit_error = self._take_worker_exit_error()
        if worker_exit_error is not None:
            raise worker_exit_error

    def _run(self) -> None:
        exit_error: Exception | None = None
        while True:
            try:
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
            except Exception as exc:
                exit_error = exc
                break

        with self._lock:
            self._worker_exit_error = exit_error
            self._started = False
            self._accepting_commands = False

    def _drain_commands(self) -> bool:
        while True:
            try:
                action, payload, future = self._command_queue.get_nowait()
            except queue.Empty:
                return False

            if action == "shutdown":
                try:
                    self._shutdown_worker()
                finally:
                    self._fail_pending_commands("ACQ_SHUTDOWN")
                return True
            try:
                if action == "start_recording":
                    root_dir, session_name, recording_label, recording_descriptors = payload
                    self._start_recording_worker(
                        str(root_dir),
                        str(session_name),
                        recording_label,
                        recording_descriptors,
                    )
                elif action == "stop_recording":
                    self._stop_recording_worker()
                elif action == "add_marker":
                    self._add_marker_worker(payload)
                elif action == "add_segment":
                    start_ns, end_ns, label = payload
                    self._add_segment_worker(start_ns, end_ns, label)
                else:
                    raise RuntimeError(f"ACQ_UNKNOWN_COMMAND: {action}")
            except Exception as exc:
                if future is not None and not future.done():
                    future.set_exception(exc)
                continue

            if future is not None and not future.done():
                future.set_result(None)

    def _on_frame_worker(self, frame: object) -> None:
        if not isinstance(frame, FrameEnvelope):
            return
        if self._storage is None:
            return

        try:
            self._storage.append_frame(frame)
        except Exception:
            self._fail_recording_worker("write_failed")

    def _start_recording_worker(
        self,
        root_dir: str,
        session_name: str,
        recording_label: object,
        recording_descriptors: object,
    ) -> None:
        if self._storage is not None:
            raise RuntimeError("ACQ_ALREADY_RECORDING")

        if not session_name.strip():
            raise RuntimeError("ACQ_INVALID_SESSION_NAME")

        if not isinstance(recording_descriptors, dict) or not all(
            isinstance(value, StreamDescriptor)
            for value in recording_descriptors.values()
        ):
            raise RuntimeError("ACQ_INVALID_DESCRIPTOR_SNAPSHOT")

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
            raise RuntimeError(f"ACQ_START_FAILED: {type(exc).__name__}: {exc}") from exc

        self._set_state("recording")

    def _stop_recording_worker(self) -> None:
        self._stop_recording_worker_with_policy(publish_failure=True)

    def _stop_recording_worker_with_policy(self, *, publish_failure: bool) -> None:
        if self._storage is None:
            raise RuntimeError("ACQ_STOP_IGNORED: not recording")

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
            if publish_failure:
                self._publish_recording_failed(
                    storage,
                    stopped_at_ns=stopped_at_ns,
                    reason=failure_reason,
                )
            raise RuntimeError(f"ACQ_STOP_FAILED: {failure_reason}")

    def _add_marker_worker(self, label: object) -> None:
        if self._storage is None:
            raise RuntimeError("ACQ_MARKER_REJECTED: not recording")

        timestamp_ns = time.time_ns()
        normalized_label = label or None
        try:
            self._storage.add_marker(timestamp_ns=timestamp_ns, label=normalized_label)
        except Exception as exc:
            raise RuntimeError(f"ACQ_MARKER_FAILED: {type(exc).__name__}: {exc}") from exc

    def _add_segment_worker(
        self,
        start_ns: object,
        end_ns: object,
        label: object,
    ) -> None:
        if self._storage is None:
            raise RuntimeError("ACQ_SEGMENT_REJECTED: not recording")

        try:
            start_value = int(start_ns)
            end_value = int(end_ns)
        except (TypeError, ValueError):
            raise RuntimeError("ACQ_INVALID_SEGMENT_RANGE")

        if start_value > end_value:
            raise RuntimeError("ACQ_INVALID_SEGMENT_RANGE: start_ns > end_ns")

        normalized_label = label or None
        try:
            self._storage.add_segment(
                start_ns=start_value,
                end_ns=end_value,
                label=normalized_label,
            )
        except Exception as exc:
            raise RuntimeError(f"ACQ_SEGMENT_FAILED: {type(exc).__name__}: {exc}") from exc

    def _handle_frame_stream_overflow(self, consumer_name: str) -> None:
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
            self._stop_recording_worker_with_policy(publish_failure=False)

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
        except Exception:
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
            RecordingFailedEvent(
                session_name=storage.session_name,
                recording_id=storage.recording_id,
                recording_path=str(storage.recording_dir),
                frame_counts_by_stream=storage.frame_counts_by_stream,
                reason=reason,
                ts_ns=stopped_at_ns,
            )
        )

    def _set_state(self, state: str) -> None:
        with self._lock:
            if state == self._state:
                return
            self._state = state

    def _submit_command(
        self,
        action: str,
        payload: object | None = None,
    ) -> Future[None]:
        future: Future[None] = Future()
        if not self.is_started:
            future.set_exception(RuntimeError("ACQ_NOT_STARTED"))
            return future
        if not self._accepting_commands:
            future.set_exception(RuntimeError("ACQ_SHUTTING_DOWN"))
            return future
        self._command_queue.put((action, payload, future))
        return future

    def _fail_pending_commands(self, message: str) -> None:
        while True:
            try:
                _action, _payload, future = self._command_queue.get_nowait()
            except queue.Empty:
                return
            if future is None or future.done():
                continue
            future.set_exception(RuntimeError(message))

    def _finalize_shutdown(self) -> None:
        self._set_state("idle")
        self._started = False
        self._accepting_commands = True
        self._thread = None
        if self._frame_stream is not None:
            self._frame_stream.close()
            self._frame_stream = None

    def _take_worker_exit_error(self) -> Exception | None:
        with self._lock:
            error = self._worker_exit_error
            self._worker_exit_error = None
            return error


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
