from __future__ import annotations

from collections.abc import Callable
import threading
from uuid import uuid4

from modlink_sdk import (
    Driver,
    DriverContext,
    DriverFactory,
    DriverHost,
    DriverTimerHandle,
    FrameEnvelope,
    SearchResult,
    StreamDescriptor,
)

from ...runtime.worker import WorkerThread
from .state import DeviceState
from .task import DriverTask


class DriverRuntime:
    def __init__(
        self,
        driver_factory: DriverFactory,
        *,
        on_error: Callable[[str], None],
        on_frame: Callable[[FrameEnvelope], None],
        on_state_changed: Callable[[], None],
        parent: object | None = None,
    ) -> None:
        self._parent = parent
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
        self._driver.attach_host(DriverHost(timer_sink=self._call_later))
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
        self._thread_name = f"modlink.driver.{self._driver_id.strip()}"
        self._state = DeviceState(
            device_id=self._driver_id,
            display_name=self._display_name,
            parent=parent,
        )
        self._pending_tasks: dict[str, DriverTask] = {}
        self._lock = threading.RLock()
        self._worker = WorkerThread(
            self._thread_name,
            on_started=self._driver.on_runtime_started,
            on_stopped=self._shutdown_driver,
            on_exit=self._on_worker_exit,
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
    def is_running(self) -> bool:
        return self._worker.is_running

    @property
    def state(self) -> DeviceState:
        return self._state

    def descriptors(self) -> list[StreamDescriptor]:
        return list(self._descriptors)

    def start(self) -> None:
        if self.is_running:
            return
        self._worker.start()
        self._notify_state_changed()

    def stop(self, *, timeout_ms: int = 3000) -> None:
        if not self.is_running:
            self._state._mark_disconnected()
            self._notify_state_changed()
            return

        if not self._worker.stop(timeout_ms=timeout_ms):
            self._emit_error(
                f"DRIVER_STOP_TIMEOUT: driver_id={self.driver_id}: timeout_ms={timeout_ms}"
            )

    def search(self, provider: str) -> DriverTask:
        return self._dispatch_task("search", provider)

    def connect_device(self, config: SearchResult) -> DriverTask:
        return self._dispatch_task("connect_device", config)

    def disconnect_device(self) -> DriverTask:
        return self._dispatch_task("disconnect_device")

    def start_streaming(self) -> DriverTask:
        return self._dispatch_task("start_streaming")

    def stop_streaming(self) -> DriverTask:
        return self._dispatch_task("stop_streaming")

    def _dispatch_task(self, action: str, request: object | None = None) -> DriverTask:
        task_id = uuid4().hex
        task = DriverTask(
            task_id=task_id,
            action=action,
            request=request,
            parent=self._parent,
        )
        if not self.is_running:
            task._fail(
                RuntimeError(
                    f"driver runtime is not running: driver_id={self.driver_id}"
                )
            )
            return task

        with self._lock:
            self._pending_tasks[task_id] = task
        posted = self._worker.post(
            lambda: self._execute_task(action, task_id, request)
        )
        if not posted:
            with self._lock:
                self._pending_tasks.pop(task_id, None)
            task._fail(
                RuntimeError(
                    f"driver runtime is not running: driver_id={self.driver_id}"
                )
            )
        return task

    def _execute_task(
        self,
        action: str,
        task_id: str | None,
        request: object | None,
    ) -> None:
        if task_id is None:
            return
        with self._lock:
            task = self._pending_tasks.get(task_id)
        if task is None:
            return

        try:
            result = self._invoke_driver(action, request)
        except Exception as exc:
            self._complete_task(task_id, task, action, error=exc)
            return

        self._complete_task(task_id, task, action, result=result)

    def _complete_task(
        self,
        task_id: str,
        task: DriverTask,
        action: str,
        *,
        result: object | None = None,
        error: Exception | None = None,
    ) -> None:
        with self._lock:
            self._pending_tasks.pop(task_id, None)
        if error is not None:
            task._fail(error)
            self._emit_error(
                f"DRIVER_CALL_FAILED: driver_id={self.driver_id}: "
                f"action={action}: {type(error).__name__}: {error}"
            )
            return
        task._finish(result)
        self._update_state_for_completed_task(task)

    def _invoke_driver(self, action: str, request: object | None) -> object | None:
        method = getattr(self._driver, action, None)
        if not callable(method):
            raise AttributeError(
                f"driver does not support action '{action}': driver_id={self.driver_id}"
            )
        if request is None:
            return method()
        return method(request)

    def _fail_pending_tasks(
        self,
        error: Exception | None,
        *,
        default_message: str,
    ) -> None:
        with self._lock:
            pending = list(self._pending_tasks.values())
            self._pending_tasks.clear()
        if not pending:
            return
        message = str(error) if error is not None else default_message
        for task in pending:
            task._fail(RuntimeError(message))

    def _update_state_for_completed_task(self, task: DriverTask) -> None:
        if task.error is not None:
            return
        if task.action == "connect_device":
            self._state._mark_connected()
            self._notify_state_changed()
            return
        if task.action == "disconnect_device":
            self._state._mark_disconnected()
            self._notify_state_changed()
            return
        if task.action == "start_streaming":
            self._state._mark_streaming_started()
            self._notify_state_changed()
            return
        if task.action == "stop_streaming":
            self._state._mark_streaming_stopped()
            self._notify_state_changed()

    def _notify_state_changed(self) -> None:
        self._on_state_changed()

    def _on_driver_frame(self, frame: FrameEnvelope) -> None:
        self._on_frame(frame)

    def _on_driver_connection_lost(self, detail: object) -> None:
        self._state._mark_connection_lost()
        detail_text = str(detail).strip()
        message = (
            f"DRIVER_CONNECTION_LOST: {detail_text}"
            if detail_text
            else "DRIVER_CONNECTION_LOST"
        )
        self._emit_error(message)
        self._notify_state_changed()

    def _emit_error(self, message: str) -> None:
        self._on_error(message)

    def _call_later(
        self,
        delay_ms: float,
        callback: Callable[[], None],
    ) -> DriverTimerHandle:
        if not callable(callback):
            raise TypeError("timer callback must be callable")
        timer_id = self._worker.call_later(
            max(0.0, float(delay_ms)),
            lambda: self._run_timer_callback(callback),
        )
        return DriverTimerHandle(timer_id, cancel_sink=self._cancel_timer)

    def _cancel_timer(self, timer_id: str) -> None:
        self._worker.cancel_timer(timer_id)

    def _run_timer_callback(self, callback: Callable[[], None]) -> None:
        try:
            callback()
        except Exception as exc:
            self._emit_error(
                f"DRIVER_TIMER_FAILED: driver_id={self.driver_id}: "
                f"{type(exc).__name__}: {exc}"
            )

    def _shutdown_driver(self) -> None:
        try:
            self._driver.on_shutdown()
        except Exception as exc:
            self._emit_error(
                f"DRIVER_SHUTDOWN_FAILED: driver_id={self.driver_id}: "
                f"{type(exc).__name__}: {exc}"
            )

    def _on_worker_exit(self, stop_reason: Exception | None) -> None:
        if stop_reason is not None:
            self._emit_error(
                f"DRIVER_THREAD_FAILED: driver_id={self.driver_id}: "
                f"{type(stop_reason).__name__}: {stop_reason}"
            )
        self._state._mark_disconnected()
        self._notify_state_changed()
        self._fail_pending_tasks(
            stop_reason,
            default_message=(
                "driver thread stopped before pending tasks completed: "
                f"driver_id={self.driver_id}"
            ),
        )

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
