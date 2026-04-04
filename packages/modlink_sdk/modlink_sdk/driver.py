"""Driver base classes exposed by the ModLink SDK."""

from __future__ import annotations

from collections.abc import Callable
from threading import Event, RLock, Thread, current_thread

from .models import FrameEnvelope, SearchResult, StreamDescriptor


class DriverContext:
    """Runtime callbacks exposed to one driver instance.

    The host may close a context during shutdown. After closure, late frames
    and late connection-lost notifications are ignored so helper threads
    cannot mutate host state after teardown.
    """

    def __init__(
        self,
        *,
        frame_sink: Callable[[FrameEnvelope], object | None],
        connection_lost_sink: Callable[[object], None],
    ) -> None:
        self._frame_sink = frame_sink
        self._connection_lost_sink = connection_lost_sink
        self._lock = RLock()
        self._closed = False

    def emit_frame(self, frame: FrameEnvelope) -> bool:
        with self._lock:
            if self._closed:
                return False
            result = self._frame_sink(frame)
            return result is not False

    def emit_connection_lost(self, detail: object) -> None:
        with self._lock:
            if self._closed:
                return
            self._connection_lost_sink(detail)

    def _close(self) -> None:
        with self._lock:
            self._closed = True


class Driver:
    """Base class for all ModLink drivers.

    A driver instance represents one host-managed device endpoint. The host
    loads the driver through a zero-argument factory, reads its static
    metadata, and then executes lifecycle methods on a dedicated worker
    thread.

    General contract:

    - ``device_id`` must be stable, non-empty, and use ``name.XX`` form.
    - ``descriptors()`` must describe every stream the driver may emit.
    - control methods are synchronous and run on the driver worker thread.
    - ``start_streaming()`` should return quickly after streaming begins.
    - one driver instance manages at most one active device connection.
    """

    supported_providers: tuple[str, ...] = ()
    """Provider identifiers accepted by ``search()``."""

    @property
    def device_id(self) -> str:
        raise NotImplementedError(f"{type(self).__name__} must implement device_id")

    def __init__(self) -> None:
        self._context: DriverContext | None = None

    @property
    def display_name(self) -> str:
        return self.device_id

    def bind(self, context: DriverContext) -> None:
        """Attach the host runtime context to this driver instance."""
        self._context = context

    def on_runtime_started(self) -> None:
        """Optional hook called after the driver worker thread starts."""

    def descriptors(self) -> list[StreamDescriptor]:
        raise NotImplementedError(f"{type(self).__name__} must implement descriptors")

    def on_shutdown(self) -> None:
        """Optional hook called before the driver worker thread exits.

        Override to release resources, close connections, etc.
        """

    def emit_frame(self, frame: FrameEnvelope) -> bool:
        return self._require_context().emit_frame(frame)

    def emit_connection_lost(self, detail: object) -> None:
        self._require_context().emit_connection_lost(detail)

    def _require_context(self) -> DriverContext:
        if self._context is None:
            raise RuntimeError("driver is not bound to a runtime context")
        return self._context

    def search(self, provider: str) -> list[SearchResult]:
        raise NotImplementedError(f"{type(self).__name__} must implement search")

    def connect_device(self, config: SearchResult) -> None:
        raise NotImplementedError(
            f"{type(self).__name__} must implement connect_device if it supports connecting"
        )

    def disconnect_device(self) -> None:
        raise NotImplementedError(
            f"{type(self).__name__} must implement disconnect_device if it supports connecting"
        )

    def start_streaming(self) -> None:
        raise NotImplementedError(f"{type(self).__name__} must implement start_streaming")

    def stop_streaming(self) -> None:
        raise NotImplementedError(f"{type(self).__name__} must implement stop_streaming")


DriverFactory = Callable[[], Driver]


class LoopDriver(Driver):
    """Convenience base class for bounded polling drivers with a helper thread.

    This helper favors simple driver code over strict shutdown guarantees.
    ``loop()`` should stay bounded and return quickly. Long blocking or
    non-interruptible I/O belongs in a custom ``Driver`` implementation.
    The host only guarantees that frames and connection-lost callbacks are
    ignored after shutdown; it does not guarantee the helper thread has
    already finished by the time teardown returns.
    """

    loop_interval_ms = 10

    def __init__(self) -> None:
        super().__init__()
        self._loop_lock = RLock()
        self._loop_thread: Thread | None = None
        self._loop_stop: Event | None = None

    @property
    def is_looping(self) -> bool:
        with self._loop_lock:
            thread = self._loop_thread
            return thread is not None and thread.is_alive()

    def start_streaming(self) -> None:
        with self._loop_lock:
            thread = self._loop_thread
            if thread is not None and thread.is_alive():
                return
        self.on_loop_started()
        stop_event = Event()
        thread = Thread(
            target=self._run_loop_thread,
            args=(stop_event,),
            name=f"modlink.loop.{self.device_id.strip()}",
            daemon=True,
        )
        with self._loop_lock:
            self._loop_stop = stop_event
            self._loop_thread = thread
        thread.start()

    def stop_streaming(self) -> None:
        with self._loop_lock:
            stop_event = self._loop_stop
            thread = self._loop_thread
        if stop_event is None or thread is None:
            return
        stop_event.set()
        if thread is not current_thread():
            thread.join(timeout=2.0)

    def on_loop_started(self) -> None:
        """Optional hook called once before loop execution starts."""

    def on_loop_stopped(self) -> None:
        """Optional hook called once after loop execution stops."""

    def loop(self) -> None:
        raise NotImplementedError(f"{type(self).__name__} must implement loop")

    def on_shutdown(self) -> None:
        """Best-effort shutdown hook for the helper loop thread."""
        self.stop_streaming()

    def _run_loop_thread(self, stop_event: Event) -> None:
        interval_seconds = max(0.0, float(self.loop_interval_ms)) / 1000.0
        try:
            while not stop_event.wait(interval_seconds):
                self.loop()
        except Exception as exc:
            self.emit_connection_lost(f"LOOP_FAILED: {type(exc).__name__}: {exc}")
        finally:
            with self._loop_lock:
                if self._loop_stop is stop_event:
                    self._loop_stop = None
                if self._loop_thread is current_thread():
                    self._loop_thread = None
            self.on_loop_stopped()
