"""Driver base classes exposed by the ModLink SDK."""

from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from .models import FrameEnvelope, SearchResult, StreamDescriptor


class Driver(QObject):
    """Base class for all ModLink drivers.

    A driver instance represents one host-managed device endpoint. The host
    loads the driver through a zero-argument factory, reads its static
    metadata, and then executes lifecycle methods on a dedicated worker
    thread.

    General contract:

    - ``device_id`` must be stable and non-empty.
    - ``descriptors()`` must describe every stream the driver may emit.
    - control methods are synchronous and run on the driver worker thread.
    - ``start_streaming()`` should return quickly after acquisition starts.
    - one driver instance manages at most one active device connection.
    """

    sig_frame = pyqtSignal(FrameEnvelope)
    """Emitted when a new payload chunk is available.

    The emitted ``stream_id`` must match one of the driver's registered
    ``StreamDescriptor.stream_id`` values.
    """

    sig_connection_lost = pyqtSignal(object)
    """Emitted when a previously connected device becomes unavailable.

    The payload is intentionally unconstrained so drivers can include
    transport-specific diagnostics.
    """

    supported_providers: tuple[str, ...] = ()
    """Provider identifiers accepted by ``search()``.

    The host passes the selected provider string through unchanged.
    """

    @property
    def device_id(self) -> str:
        """Return the stable identifier of this driver instance.

        The value must be non-empty, stable for the lifetime of the instance,
        and independent of connection state.
        """
        raise NotImplementedError(f"{type(self).__name__} must implement device_id")

    @property
    def display_name(self) -> str:
        """Return the human-readable driver label.

        The default implementation reuses ``device_id``.
        """
        return self.device_id

    def on_thread_started(self) -> None:
        """Optional hook called after the driver worker thread starts.

        Most drivers do not need to override this. It mainly exists for cases
        where thread-local objects, such as ``QTimer``, must be created on the
        driver thread itself.
        """

    def descriptors(self) -> list[StreamDescriptor]:
        """Return the streams exposed by this driver.

        Hosts may call this before a device is connected. The returned
        descriptors should remain stable for the lifetime of the driver
        instance.
        """
        raise NotImplementedError(f"{type(self).__name__} must implement descriptors")

    def shutdown(self) -> None:
        """Run best-effort shutdown cleanup.

        The default implementation stops streaming and then disconnects the
        device. ``NotImplementedError`` from either operation is ignored so the
        method remains safe for partial driver implementations.
        """
        try:
            self.stop_streaming()
        except NotImplementedError:
            pass
        try:
            self.disconnect_device()
        except NotImplementedError:
            pass

    def search(self, provider: str) -> list[SearchResult]:
        """Return discovery candidates for ``provider``.

        This is a one-shot call. Each returned ``SearchResult`` is suitable for
        presentation in a selection UI and may later be passed back to
        ``connect_device()``.
        """
        raise NotImplementedError(f"{type(self).__name__} must implement search")

    def connect_device(self, config: SearchResult) -> None:
        """Connect to a previously discovered device candidate.

        ``config`` is normally one ``SearchResult`` returned by ``search()``.
        The method should establish communication and prepare runtime
        resources, but it must not start live acquisition yet.
        """
        raise NotImplementedError(
            f"{type(self).__name__} must implement connect_device if it supports connecting"
        )

    def disconnect_device(self) -> None:
        """Disconnect the current device.

        The method should be idempotent and leave the driver in a consistent
        disconnected state.
        """
        raise NotImplementedError(
            f"{type(self).__name__} must implement disconnect_device if it supports connecting"
        )

    def start_streaming(self) -> None:
        """Start live acquisition.

        The method should return quickly and begin producing ``sig_frame``
        emissions through callbacks, timers, or another non-blocking mechanism.
        """
        raise NotImplementedError(
            f"{type(self).__name__} must implement start_streaming"
        )

    def stop_streaming(self) -> None:
        """Stop live acquisition and release stream-specific resources."""
        raise NotImplementedError(
            f"{type(self).__name__} must implement stop_streaming"
        )


DriverFactory = Callable[[], Driver]


class LoopDriver(Driver):
    """Convenience base class for timer-driven loop-style drivers.

    ``LoopDriver`` is intended for common polling-style devices where one
    short method can be called repeatedly to check for fresh data. It already
    satisfies the normal ``Driver`` streaming contract, so it works with the
    existing runtime without any core changes.

    Typical subclass responsibilities:

    - implement ``search()``, ``connect_device()``, ``disconnect_device()``,
      and ``descriptors()`` as usual
    - implement ``loop()`` for one short iteration
    - optionally override ``loop_interval_ms``
    - optionally implement ``on_loop_started()`` and ``on_loop_stopped()``
    """

    loop_interval_ms = 10
    """Driver-level timer cadence used by ``start_streaming()``.

    This is not a stream sample rate. A single loop may emit zero, one, or
    multiple payloads, and different streams may still run at different
    effective rates within the same driver.
    """

    def __init__(self) -> None:
        super().__init__()
        self._loop_timer: QTimer | None = None

    def on_thread_started(self) -> None:
        """Create the loop timer on the driver worker thread."""
        self._loop_timer = QTimer(self)
        self._loop_timer.timeout.connect(self.loop)

    def start_streaming(self) -> None:
        """Start timer-driven looping.

        The default implementation calls ``on_loop_started()`` once and then
        schedules repeated ``loop()`` calls on the driver thread.
        """
        if self._loop_timer is None:
            raise RuntimeError("loop timer is not ready")
        if self._loop_timer.isActive():
            return

        self.on_loop_started()
        self._loop_timer.start(int(self.loop_interval_ms))

    def stop_streaming(self) -> None:
        """Stop timer-driven looping.

        The default implementation stops future ``loop()`` calls and then
        calls ``on_loop_stopped()`` once.
        """
        if self._loop_timer is None or not self._loop_timer.isActive():
            return

        self._loop_timer.stop()
        self.on_loop_stopped()

    def on_loop_started(self) -> None:
        """Optional hook called once before the loop timer starts."""

    def on_loop_stopped(self) -> None:
        """Optional hook called once after the loop timer stops."""

    def loop(self) -> None:
        """Run one short loop iteration.

        The method should stay short and non-blocking. It may emit one or more
        frames, or no frames if no fresh data is available. Think of this as
        an Arduino-style ``loop()`` running on the driver thread.
        """
        raise NotImplementedError(f"{type(self).__name__} must implement loop")
