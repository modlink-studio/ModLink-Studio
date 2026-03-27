from __future__ import annotations

from collections.abc import Callable

from modlink_sdk import DriverFactory, SearchResult, StreamDescriptor
from modlink_sdk import FrameEnvelope

from ...events import (
    BackendErrorEvent,
    BackendEventQueue,
    DriverSnapshot,
    DriverStateChangedEvent,
    DriverTaskFinishedEvent,
)

from .runtime import DriverRuntime
from .state import DeviceState
from .task import DriverTask


class DriverPortal:
    """Public driver-facing gateway used by the rest of the system."""

    def __init__(
        self,
        driver_factory: DriverFactory,
        *,
        event_queue: BackendEventQueue,
        frame_sink: Callable[[FrameEnvelope], None] | None = None,
        thread_name: str | None = None,
        parent: object | None = None,
    ) -> None:
        self._parent = parent
        self._event_queue = event_queue
        self._frame_sink = frame_sink
        self._runtime = DriverRuntime(
            driver_factory,
            on_error=self._on_runtime_error,
            on_frame=self._on_runtime_frame,
            on_connection_lost=self._on_runtime_connection_lost,
            on_status_changed=self._on_runtime_status_changed,
            thread_name=thread_name,
            parent=parent,
        )
        self._state = DeviceState(
            device_id=self._runtime.driver_id,
            display_name=self._runtime.display_name,
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
        return self._state.is_connected

    @property
    def is_streaming(self) -> bool:
        return self._state.is_streaming

    @property
    def state(self) -> DeviceState:
        return self._state

    def snapshot(self) -> DriverSnapshot:
        return DriverSnapshot(
            driver_id=self.driver_id,
            display_name=self.display_name,
            supported_providers=self.supported_providers,
            is_running=self.is_running,
            is_connected=self.is_connected,
            is_streaming=self.is_streaming,
            status=self._state.status,
            status_detail=self._state.status_detail,
        )

    def descriptors(self) -> list[StreamDescriptor]:
        return self._runtime.descriptors()

    def start(self) -> None:
        self._runtime.start()
        self._publish_state_changed()

    def stop(self, *, timeout_ms: int = 3000) -> None:
        self._runtime.stop(timeout_ms=timeout_ms)
        self._state._mark_disconnected()
        self._publish_state_changed()

    def search(self, provider: str) -> DriverTask:
        task = self._runtime.search(provider)
        task.add_done_callback(self._publish_task_finished)
        return task

    def connect_device(self, config: SearchResult) -> DriverTask:
        task = self._runtime.connect_device(config)
        task.add_done_callback(self._on_connect_done)
        return task

    def disconnect_device(self) -> DriverTask:
        task = self._runtime.disconnect_device()
        task.add_done_callback(self._on_disconnect_done)
        return task

    def start_streaming(self) -> DriverTask:
        task = self._runtime.start_streaming()
        task.add_done_callback(self._on_start_streaming_done)
        return task

    def stop_streaming(self) -> DriverTask:
        task = self._runtime.stop_streaming()
        task.add_done_callback(self._on_stop_streaming_done)
        return task

    def _on_connect_done(self, task: DriverTask) -> None:
        if task.error is None:
            self._state._mark_connected()
            self._publish_state_changed()
        self._publish_task_finished(task)

    def _on_disconnect_done(self, task: DriverTask) -> None:
        if task.error is None:
            self._state._mark_disconnected()
            self._publish_state_changed()
        self._publish_task_finished(task)

    def _on_start_streaming_done(self, task: DriverTask) -> None:
        if task.error is None:
            self._state._mark_streaming_started()
            self._publish_state_changed()
        self._publish_task_finished(task)

    def _on_stop_streaming_done(self, task: DriverTask) -> None:
        if task.error is None:
            self._state._mark_streaming_stopped()
            self._publish_state_changed()
        self._publish_task_finished(task)

    def _on_runtime_frame(self, frame: FrameEnvelope) -> None:
        if self._frame_sink is not None:
            self._frame_sink(frame)

    def _on_runtime_connection_lost(self, detail: object) -> None:
        self._state._mark_connection_lost(detail)
        self._publish_state_changed()

    def _on_runtime_status_changed(self, status: str, detail: object | None) -> None:
        self._state._mark_status(status, detail)
        self._publish_state_changed()

    def _on_runtime_error(self, message: str) -> None:
        self._event_queue.publish(
            BackendErrorEvent(source=f"driver:{self.driver_id}", message=message)
        )

    def _publish_state_changed(self) -> None:
        self._event_queue.publish(DriverStateChangedEvent(snapshot=self.snapshot()))

    def _publish_task_finished(self, task: DriverTask) -> None:
        error_message = None if task.error is None else str(task.error)
        self._event_queue.publish(
            DriverTaskFinishedEvent(
                driver_id=self.driver_id,
                task_id=task.task_id,
                action=task.action,
                state=task.state,
                request=task.request,
                result=task.result,
                error_message=error_message,
            )
        )
