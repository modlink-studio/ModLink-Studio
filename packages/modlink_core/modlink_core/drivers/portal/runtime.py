from __future__ import annotations

from collections.abc import Callable
import threading
from uuid import uuid4

from modlink_sdk import (
    DriverFactory,
    DriverHost,
    DriverTimerHandle,
    FrameEnvelope,
    SearchResult,
    StreamDescriptor,
)

from ...runtime.worker import WorkerThread
from .session import DriverSession
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
        self._session = DriverSession(
            driver_factory,
            on_error=on_error,
            on_frame=on_frame,
            on_state_changed=on_state_changed,
            parent=parent,
        )
        self._pending_tasks: dict[str, DriverTask] = {}
        self._lock = threading.RLock()
        self._worker = WorkerThread(
            f"modlink.driver.{self.driver_id.strip()}",
            on_started=self._session.on_worker_started,
            on_stopped=self._session.on_worker_stopped,
            on_exit=self._on_worker_exit,
        )
        self._session.attach_host(DriverHost(timer_sink=self._call_later))

    @property
    def driver_id(self) -> str:
        return self._session.driver_id

    @property
    def display_name(self) -> str:
        return self._session.display_name

    @property
    def supported_providers(self) -> tuple[str, ...]:
        return self._session.supported_providers

    @property
    def is_running(self) -> bool:
        return self._worker.is_running

    @property
    def state(self) -> DeviceState:
        return self._session.state

    def descriptors(self) -> list[StreamDescriptor]:
        return self._session.descriptors()

    def start(self) -> None:
        if self.is_running:
            return
        self._worker.start()
        self._session.notify_state_changed()

    def stop(self, *, timeout_ms: int = 3000) -> None:
        if not self.is_running:
            self._session.mark_stopped()
            return

        if not self._worker.stop(timeout_ms=timeout_ms):
            self._session.emit_error(
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
            result = self._session.execute(action, request)
        except Exception as exc:
            self._complete_task(task_id, task, error=exc)
            return

        self._complete_task(task_id, task, result=result)

    def _complete_task(
        self,
        task_id: str,
        task: DriverTask,
        *,
        result: object | None = None,
        error: Exception | None = None,
    ) -> None:
        with self._lock:
            self._pending_tasks.pop(task_id, None)
        if error is not None:
            task._fail(error)
            return
        task._finish(result)

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
            self._session.on_timer_failed(exc)

    def _on_worker_exit(self, stop_reason: Exception | None) -> None:
        self._session.on_worker_exit(stop_reason)
        self._fail_pending_tasks(
            stop_reason,
            default_message=(
                "driver thread stopped before pending tasks completed: "
                f"driver_id={self.driver_id}"
            ),
        )
