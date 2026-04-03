from __future__ import annotations

from collections.abc import Callable

from modlink_sdk import Driver, DriverContext, DriverFactory, FrameEnvelope, SearchResult, StreamDescriptor

from ...events import DriverSnapshot
from .state import DeviceState


class DriverSession:
    """Owns one bound driver instance plus its concrete driver state."""

    def __init__(
        self,
        driver_factory: DriverFactory,
        *,
        on_connection_lost: Callable[[object | None], None],
        on_frame: Callable[[FrameEnvelope], object | None],
        parent: object | None = None,
    ) -> None:
        self._on_connection_lost = on_connection_lost
        self._on_frame = on_frame
        self._driver = self._create_driver(driver_factory)
        self._context = DriverContext(
            frame_sink=self._on_driver_frame,
            connection_lost_sink=self._on_driver_connection_lost,
        )
        self._driver.bind(self._context)
        self._driver_id = self._driver.device_id
        self._display_name = self._driver.display_name
        self._supported_providers = tuple(
            provider
            for provider in (
                str(item).strip() for item in self._driver.supported_providers
            )
            if provider
        )
        self._descriptors = list(self._driver.descriptors())
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

    def descriptors(self) -> list[StreamDescriptor]:
        return list(self._descriptors)

    def snapshot(self, *, is_running: bool) -> DriverSnapshot:
        is_connected, is_streaming = self._state.snapshot()
        return DriverSnapshot(
            driver_id=self.driver_id,
            display_name=self.display_name,
            supported_providers=self.supported_providers,
            is_running=is_running,
            is_connected=is_connected,
            is_streaming=is_streaming,
        )

    def on_executor_started(self) -> None:
        self._driver.on_runtime_started()

    def on_executor_stopped(self) -> None:
        self.close_context()
        self._driver.on_shutdown()

    def search(self, provider: str) -> list[SearchResult]:
        return self._driver.search(provider)

    def connect_device(self, config: SearchResult) -> None:
        self._driver.connect_device(config)
        self._state._mark_connected()

    def disconnect_device(self) -> None:
        self._driver.disconnect_device()
        self._state._mark_disconnected()

    def start_streaming(self) -> None:
        self._driver.start_streaming()
        self._state._mark_streaming_started()

    def stop_streaming(self) -> None:
        self._driver.stop_streaming()
        self._state._mark_streaming_stopped()

    def mark_stopped(self) -> None:
        self._state._mark_disconnected()

    def close_context(self) -> None:
        self._context._close()

    def _on_driver_frame(self, frame: FrameEnvelope) -> bool:
        result = self._on_frame(frame)
        return result is not False

    def _on_driver_connection_lost(self, detail: object) -> None:
        if not self._state._mark_connection_lost():
            return
        self._on_connection_lost(_normalize_connection_detail(detail))

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


def _normalize_connection_detail(detail: object) -> object | None:
    if isinstance(detail, str):
        normalized = detail.strip()
        return normalized or None
    return detail
