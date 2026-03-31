from __future__ import annotations

from collections.abc import Callable

from modlink_sdk import (
    Driver,
    DriverContext,
    DriverFactory,
    DriverHost,
    FrameEnvelope,
    StreamDescriptor,
)

from .state import DeviceState


class DriverSession:
    """Owns one bound driver instance plus its domain state."""

    def __init__(
        self,
        driver_factory: DriverFactory,
        *,
        on_error: Callable[[str], None],
        on_frame: Callable[[FrameEnvelope], None],
        on_state_changed: Callable[[], None],
        parent: object | None = None,
    ) -> None:
        self._on_error = on_error
        self._on_frame = on_frame
        self._on_state_changed = on_state_changed
        self._driver = self._create_driver(driver_factory)
        self._driver.bind(
            DriverContext(
                frame_sink=self._on_driver_frame,
                connection_lost_sink=self._on_driver_connection_lost,
            )
        )
        self._driver_id = self._driver.device_id
        self._display_name = self._driver.display_name
        self._supported_providers = tuple(
            provider
            for provider in (
                str(item).strip() for item in self._driver.supported_providers
            )
            if provider
        )
        self._descriptors = self._driver.descriptors()
        self._state = DeviceState(
            device_id=self._driver_id,
            display_name=self._display_name,
            parent=parent,
        )

    @property
    def driver_id(self) -> str:
        return self._driver_id

    @property
    def display_name(self) -> str:
        return self._display_name

    @property
    def supported_providers(self) -> tuple[str, ...]:
        return self._supported_providers

    @property
    def state(self) -> DeviceState:
        return self._state

    def attach_host(self, host: DriverHost) -> None:
        self._driver.attach_host(host)

    def descriptors(self) -> list[StreamDescriptor]:
        return list(self._descriptors)

    def on_worker_started(self) -> None:
        self._driver.on_runtime_started()

    def on_worker_stopped(self) -> None:
        try:
            self._driver.on_shutdown()
        except Exception as exc:
            self._emit_error(
                f"DRIVER_SHUTDOWN_FAILED: driver_id={self.driver_id}: "
                f"{type(exc).__name__}: {exc}"
            )

    def on_worker_exit(self, stop_reason: Exception | None) -> None:
        if stop_reason is not None:
            self._emit_error(
                f"DRIVER_THREAD_FAILED: driver_id={self.driver_id}: "
                f"{type(stop_reason).__name__}: {stop_reason}"
            )
        self._mark_disconnected()

    def execute(self, action: str, request: object | None) -> object | None:
        try:
            result = self._invoke_driver(action, request)
        except Exception as exc:
            self._emit_error(
                f"DRIVER_CALL_FAILED: driver_id={self.driver_id}: "
                f"action={action}: {type(exc).__name__}: {exc}"
            )
            raise
        self._update_state_for_completed_action(action)
        return result

    def on_timer_failed(self, exc: Exception) -> None:
        self.emit_error(
            f"DRIVER_TIMER_FAILED: driver_id={self.driver_id}: "
            f"{type(exc).__name__}: {exc}"
        )

    def mark_stopped(self) -> None:
        self._mark_disconnected()

    def notify_state_changed(self) -> None:
        self._notify_state_changed()

    def emit_error(self, message: str) -> None:
        self._emit_error(str(message))

    def _invoke_driver(self, action: str, request: object | None) -> object | None:
        method = getattr(self._driver, action, None)
        if not callable(method):
            raise AttributeError(
                f"driver does not support action '{action}': driver_id={self.driver_id}"
            )
        if request is None:
            return method()
        return method(request)

    def _update_state_for_completed_action(self, action: str) -> None:
        if action == "connect_device":
            self._state._mark_connected()
            self._notify_state_changed()
            return
        if action == "disconnect_device":
            self._mark_disconnected()
            return
        if action == "start_streaming":
            self._state._mark_streaming_started()
            self._notify_state_changed()
            return
        if action == "stop_streaming":
            self._state._mark_streaming_stopped()
            self._notify_state_changed()

    def _on_driver_frame(self, frame: FrameEnvelope) -> None:
        self._on_frame(frame)

    def _on_driver_connection_lost(self, detail: object) -> None:
        detail_text = str(detail).strip()
        message = (
            f"DRIVER_CONNECTION_LOST: {detail_text}"
            if detail_text
            else "DRIVER_CONNECTION_LOST"
        )
        self._emit_error(message)
        self._state._mark_connection_lost()
        self._notify_state_changed()

    def _mark_disconnected(self) -> None:
        self._state._mark_disconnected()
        self._notify_state_changed()

    def _notify_state_changed(self) -> None:
        self._on_state_changed()

    def _emit_error(self, message: str) -> None:
        self._on_error(message)

    @staticmethod
    def _create_driver(driver_factory: DriverFactory) -> Driver:
        if not callable(driver_factory):
            raise TypeError("driver_factory must be callable")

        driver = driver_factory()
        if not isinstance(driver, Driver):
            raise TypeError("driver_factory must return a Driver instance")
        driver_id = driver.device_id.strip()
        if not driver_id:
            raise ValueError("driver.device_id must not be empty")
        return driver
