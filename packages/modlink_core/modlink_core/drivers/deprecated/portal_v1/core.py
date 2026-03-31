from __future__ import annotations

from collections.abc import Callable

from modlink_sdk import DriverFactory, FrameEnvelope, SearchResult, StreamDescriptor

from ...events import (
    BackendErrorEvent,
    BackendEvent,
    DriverSnapshot,
    DriverStateChangedEvent,
)
from .runtime import DriverRuntime
from .task import DriverTask


class DriverPortal:
    """Public driver-facing gateway used by the rest of the system."""

    def __init__(
        self,
        driver_factory: DriverFactory,
        *,
        publish_event: Callable[[BackendEvent], None],
        frame_sink: Callable[[FrameEnvelope], None] | None = None,
        parent: object | None = None,
    ) -> None:
        self._parent = parent
        self._publish_event = publish_event
        self._frame_sink = frame_sink
        self._runtime = DriverRuntime(
            driver_factory,
            on_error=self._on_runtime_error,
            on_frame=self._on_runtime_frame,
            on_state_changed=self._on_runtime_state_changed,
            parent=parent,
        )

    @property
    def driver_id(self) -> str:
        return self._runtime.driver_id

    @property
    def display_name(self) -> str:
        return self._runtime.display_name

    @property
    def supported_providers(self) -> tuple[str, ...]:
        return self._runtime.supported_providers

    @property
    def is_running(self) -> bool:
        return self._runtime.is_running

    @property
    def is_connected(self) -> bool:
        return self._runtime.state.is_connected

    @property
    def is_streaming(self) -> bool:
        return self._runtime.state.is_streaming

    @property
    def state(self):
        return self._runtime.state

    def snapshot(self) -> DriverSnapshot:
        return DriverSnapshot(
            driver_id=self.driver_id,
            display_name=self.display_name,
            supported_providers=self.supported_providers,
            is_running=self.is_running,
            is_connected=self.is_connected,
            is_streaming=self.is_streaming,
        )

    def descriptors(self) -> list[StreamDescriptor]:
        return self._runtime.descriptors()

    def start(self) -> None:
        self._runtime.start()

    def stop(self, *, timeout_ms: int = 3000) -> None:
        self._runtime.stop(timeout_ms=timeout_ms)

    def search(self, provider: str) -> DriverTask:
        return self._runtime.search(provider)

    def connect_device(self, config: SearchResult) -> DriverTask:
        return self._runtime.connect_device(config)

    def disconnect_device(self) -> DriverTask:
        return self._runtime.disconnect_device()

    def start_streaming(self) -> DriverTask:
        return self._runtime.start_streaming()

    def stop_streaming(self) -> DriverTask:
        return self._runtime.stop_streaming()

    def _on_runtime_frame(self, frame: FrameEnvelope) -> None:
        if self._frame_sink is not None:
            self._frame_sink(frame)

    def _on_runtime_state_changed(self) -> None:
        self._publish_state_changed()

    def _on_runtime_error(self, message: str) -> None:
        self._publish_event(
            BackendErrorEvent(source=f"driver:{self.driver_id}", message=message)
        )

    def _publish_state_changed(self) -> None:
        self._publish_event(DriverStateChangedEvent(snapshot=self.snapshot()))
