from __future__ import annotations

from modlink_qt import QObject, pyqtSignal

from modlink_sdk import DriverFactory, FrameEnvelope, SearchResult, StreamDescriptor

from .runtime import DriverRuntime
from .state import DeviceState
from .task import DriverTask


class DriverPortal(QObject):
    """Public driver-facing gateway used by the rest of the system."""

    sig_error = pyqtSignal(str)
    sig_frame = pyqtSignal(FrameEnvelope)
    sig_state_changed = pyqtSignal(object)
    sig_connection_lost = pyqtSignal(object)

    def __init__(
        self,
        driver_factory: DriverFactory,
        *,
        thread_name: str | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self._runtime = DriverRuntime(
            driver_factory,
            thread_name=thread_name,
            parent=self,
        )
        self._state = DeviceState(
            device_id=self._runtime.driver_id,
            display_name=self._runtime.display_name,
            parent=self,
        )

        self._runtime.sig_error.connect(self.sig_error.emit)
        self._runtime.sig_frame.connect(self.sig_frame.emit)
        self._runtime.sig_connection_lost.connect(
            self._state._mark_connection_lost
        )

        self._state.sig_state_changed.connect(self.sig_state_changed.emit)
        self._state.sig_connection_lost.connect(self.sig_connection_lost.emit)

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
        return self._state.is_connected

    @property
    def is_streaming(self) -> bool:
        return self._state.is_streaming

    @property
    def state(self) -> DeviceState:
        return self._state

    def descriptors(self) -> list[StreamDescriptor]:
        return self._runtime.descriptors()

    def start(self) -> None:
        self._runtime.start()

    def stop(self, *, timeout_ms: int = 3000) -> None:
        self._runtime.stop(timeout_ms=timeout_ms)
        self._state._mark_disconnected()

    def search(self, provider: str) -> DriverTask:
        return self._runtime.search(provider)

    def connect_device(self, config: SearchResult) -> DriverTask:
        task = self._runtime.connect_device(config)
        task.sig_done.connect(lambda: self._on_connect_done(task))
        return task

    def disconnect_device(self) -> DriverTask:
        task = self._runtime.disconnect_device()
        task.sig_done.connect(lambda: self._on_disconnect_done(task))
        return task

    def start_streaming(self) -> DriverTask:
        task = self._runtime.start_streaming()
        task.sig_done.connect(lambda: self._on_start_streaming_done(task))
        return task

    def stop_streaming(self) -> DriverTask:
        task = self._runtime.stop_streaming()
        task.sig_done.connect(lambda: self._on_stop_streaming_done(task))
        return task

    def _on_connect_done(self, task: DriverTask) -> None:
        if task.error is None:
            self._state._mark_connected()

    def _on_disconnect_done(self, task: DriverTask) -> None:
        if task.error is None:
            self._state._mark_disconnected()

    def _on_start_streaming_done(self, task: DriverTask) -> None:
        if task.error is None:
            self._state._mark_streaming_started()

    def _on_stop_streaming_done(self, task: DriverTask) -> None:
        if task.error is None:
            self._state._mark_streaming_stopped()
