"""Driver base classes exposed by the ModLink SDK."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .models import FrameEnvelope, SearchResult, StreamDescriptor


class DriverContext:
    """Runtime callbacks exposed to one driver instance."""

    def __init__(
        self,
        *,
        frame_sink: Callable[[FrameEnvelope], None],
        connection_lost_sink: Callable[[object], None],
        error_sink: Callable[[str], None],
        status_sink: Callable[[str, object | None], None],
    ) -> None:
        self._frame_sink = frame_sink
        self._connection_lost_sink = connection_lost_sink
        self._error_sink = error_sink
        self._status_sink = status_sink

    def emit_frame(self, frame: FrameEnvelope) -> None:
        self._frame_sink(frame)

    def emit_connection_lost(self, detail: object) -> None:
        self._connection_lost_sink(detail)

    def report_error(self, message: str) -> None:
        self._error_sink(str(message))

    def set_status(self, status: str, detail: object | None = None) -> None:
        normalized = str(status).strip()
        if not normalized:
            raise ValueError("driver status must not be empty")
        self._status_sink(normalized, detail)


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
        self._emissions_enabled = True
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

    def shutdown(self) -> None:
        self._emissions_enabled = False
        try:
            self.stop_streaming()
        except NotImplementedError:
            pass
        try:
            self.disconnect_device()
        except NotImplementedError:
            pass

    def emit_frame(self, frame: FrameEnvelope) -> bool:
        if not self._emissions_enabled:
            return False
        context = self._require_context()
        context.emit_frame(frame)
        return True

    def emit_connection_lost(self, payload: object) -> bool:
        if not self._emissions_enabled:
            return False
        context = self._require_context()
        context.emit_connection_lost(payload)
        return True

    def report_error(self, message: str) -> None:
        context = self._require_context()
        context.report_error(message)

    def set_status(self, status: str, detail: Any | None = None) -> None:
        context = self._require_context()
        context.set_status(status, detail)

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

    @property
    def is_looping(self) -> bool:
        return self._looping

    def start_streaming(self) -> None:
        if self._looping:
            return
        self.on_loop_started()
        self._looping = True

    def stop_streaming(self) -> None:
        if not self._looping:
            return
        self._looping = False
        self.on_loop_stopped()

    def on_loop_started(self) -> None:
        """Optional hook called once before loop execution starts."""

    def on_loop_stopped(self) -> None:
        """Optional hook called once after loop execution stops."""

    def loop(self) -> None:
        raise NotImplementedError(f"{type(self).__name__} must implement loop")
