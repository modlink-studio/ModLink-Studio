"""Driver base classes exposed by the ModLink SDK."""

from __future__ import annotations

from collections.abc import Callable
from threading import Lock

from .models import FrameEnvelope, SearchResult, StreamDescriptor


class DriverTimerHandle:
    """Cancellable timer scheduled onto the bound runtime thread."""

    def __init__(
        self,
        timer_id: str,
        *,
        cancel_sink: Callable[[str], None],
    ) -> None:
        self._timer_id = timer_id
        self._cancel_sink = cancel_sink
        self._lock = Lock()
        self._cancelled = False

    def cancel(self) -> None:
        with self._lock:
            if self._cancelled:
                return
            self._cancelled = True
        self._cancel_sink(self._timer_id)


class DriverContext:
    """Runtime callbacks exposed to one driver instance."""

    def __init__(
        self,
        *,
        frame_sink: Callable[[FrameEnvelope], None],
        connection_lost_sink: Callable[[object], None],
        timer_sink: Callable[[float, Callable[[], None]], DriverTimerHandle],
    ) -> None:
        self._frame_sink = frame_sink
        self._connection_lost_sink = connection_lost_sink
        self._timer_sink = timer_sink

    def emit_frame(self, frame: FrameEnvelope) -> None:
        self._frame_sink(frame)

    def emit_connection_lost(self, detail: object) -> None:
        self._connection_lost_sink(detail)

    def call_later(
        self,
        delay_ms: float,
        callback: Callable[[], None],
    ) -> DriverTimerHandle:
        return self._timer_sink(delay_ms, callback)


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

    def emit_frame(self, frame: FrameEnvelope) -> None:
        self._require_context().emit_frame(frame)

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
    """Convenience base class for single-threaded loop-style drivers."""

    loop_interval_ms = 10

    def __init__(self) -> None:
        super().__init__()
        self._looping = False
        self._loop_timer: DriverTimerHandle | None = None

    @property
    def is_looping(self) -> bool:
        return self._looping

    def start_streaming(self) -> None:
        if self._looping:
            return
        self.on_loop_started()
        self._looping = True
        self._arm_loop_timer()

    def stop_streaming(self) -> None:
        if not self._looping:
            return
        self._looping = False
        loop_timer = self._loop_timer
        self._loop_timer = None
        if loop_timer is not None:
            loop_timer.cancel()
        self.on_loop_stopped()

    def on_loop_started(self) -> None:
        """Optional hook called once before loop execution starts."""

    def on_loop_stopped(self) -> None:
        """Optional hook called once after loop execution stops."""

    def loop(self) -> None:
        raise NotImplementedError(f"{type(self).__name__} must implement loop")

    def _arm_loop_timer(self) -> None:
        self._loop_timer = self._require_context().call_later(
            float(self.loop_interval_ms),
            self._run_loop_once,
        )

    def _run_loop_once(self) -> None:
        if not self._looping:
            return
        try:
            self.loop()
        except Exception as exc:
            try:
                self.stop_streaming()
            finally:
                self.emit_connection_lost(
                    f"LOOP_FAILED: {type(exc).__name__}: {exc}"
                )
            return

        if self._looping:
            self._arm_loop_timer()
