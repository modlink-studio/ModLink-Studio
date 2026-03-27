from __future__ import annotations

from collections.abc import Callable
import queue
import threading
from uuid import uuid4

from modlink_sdk import (
    Driver,
    DriverContext,
    DriverFactory,
    FrameEnvelope,
    LoopDriver,
    SearchResult,
    StreamDescriptor,
)

from .task import DriverTask


class DriverRuntime:
    _STOP = "__stop_runtime__"

    def __init__(
        self,
        driver_factory: DriverFactory,
        *,
        on_error: Callable[[str], None] | None = None,
        on_frame: Callable[[FrameEnvelope], None] | None = None,
        on_connection_lost: Callable[[object], None] | None = None,
        on_status_changed: Callable[[str, object | None], None] | None = None,
        thread_name: str | None = None,
        parent: object | None = None,
    ) -> None:
        self._parent = parent
        self._on_error = on_error
        self._on_frame = on_frame
        self._on_connection_lost = on_connection_lost
        self._on_status_changed = on_status_changed
        self._driver = self._create_driver(driver_factory)
        self._driver.bind(
            DriverContext(
                frame_sink=self._on_driver_frame,
                connection_lost_sink=self._on_driver_connection_lost,
                error_sink=self._on_driver_error,
                status_sink=self._on_driver_status,
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
        self._thread_name = thread_name or f"modlink.driver.{self._driver_id.strip()}"
        self._running = False
        self._pending_tasks: dict[str, DriverTask] = {}
        self._command_queue: queue.Queue[tuple[str, str | None, object | None]] = (
            queue.Queue()
        )
        self._thread: threading.Thread | None = None
        self._lock = threading.RLock()

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
        thread = self._thread
        return self._running and thread is not None and thread.is_alive()

    def descriptors(self) -> list[StreamDescriptor]:
        return list(self._descriptors)

    def start(self) -> None:
        with self._lock:
            if self.is_running:
                return
            self._running = True
            thread = threading.Thread(
                target=self._run,
                name=self._thread_name,
                daemon=True,
            )
            self._thread = thread
            thread.start()

    def stop(self, *, timeout_ms: int = 3000) -> None:
        thread = self._thread
        if thread is None or not thread.is_alive():
            self._running = False
            return

        self._command_queue.put((self._STOP, None, None))
        thread.join(max(0, timeout_ms) / 1000)
        if thread.is_alive():
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
        self._command_queue.put((action, task_id, request))
        return task

    def _run(self) -> None:
        stop_reason: Exception | None = None
        try:
            self._driver.on_runtime_started()
            while True:
                try:
                    action, task_id, request = self._command_queue.get(
                        timeout=self._loop_timeout_seconds()
                    )
                except queue.Empty:
                    self._run_loop_iteration()
                    continue

                if action == self._STOP:
                    break
                self._execute_task(action, task_id, request)
        except Exception as exc:
            stop_reason = exc
            self._emit_error(
                f"DRIVER_THREAD_FAILED: driver_id={self.driver_id}: "
                f"{type(exc).__name__}: {exc}"
            )
        finally:
            try:
                self._driver.shutdown()
            except Exception as exc:
                self._emit_error(
                    f"DRIVER_SHUTDOWN_FAILED: driver_id={self.driver_id}: "
                    f"{type(exc).__name__}: {exc}"
                )
            self._running = False
            self._thread = None
            self._fail_pending_tasks(
                stop_reason
                or RuntimeError(
                    "driver thread stopped before pending tasks completed: "
                    f"driver_id={self.driver_id}"
                )
            )

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

    def _invoke_driver(self, action: str, request: object | None) -> object | None:
        method = getattr(self._driver, action, None)
        if not callable(method):
            raise AttributeError(
                f"driver does not support action '{action}': driver_id={self.driver_id}"
            )
        if request is None:
            return method()
        return method(request)

    def _run_loop_iteration(self) -> None:
        if not isinstance(self._driver, LoopDriver) or not self._driver.is_looping:
            return
        try:
            self._driver.loop()
        except Exception as exc:
            try:
                self._driver.stop_streaming()
            except Exception:
                pass
            self._emit_error(
                f"DRIVER_LOOP_FAILED: driver_id={self.driver_id}: "
                f"{type(exc).__name__}: {exc}"
            )

    def _loop_timeout_seconds(self) -> float | None:
        if not isinstance(self._driver, LoopDriver) or not self._driver.is_looping:
            return None
        interval_ms = max(1, int(self._driver.loop_interval_ms))
        return interval_ms / 1000.0

    def _fail_pending_tasks(self, error: Exception) -> None:
        with self._lock:
            pending = list(self._pending_tasks.values())
            self._pending_tasks.clear()
        for task in pending:
            task._fail(RuntimeError(str(error)))

    def _on_driver_frame(self, frame: FrameEnvelope) -> None:
        if self._on_frame is not None:
            self._on_frame(frame)

    def _on_driver_connection_lost(self, detail: object) -> None:
        if self._on_connection_lost is not None:
            self._on_connection_lost(detail)

    def _on_driver_error(self, message: str) -> None:
        normalized = str(message or "").strip()
        if not normalized:
            normalized = "driver reported an unspecified error"
        self._emit_error(
            f"DRIVER_REPORTED_ERROR: driver_id={self.driver_id}: {normalized}"
        )

    def _on_driver_status(self, status: str, detail: object | None) -> None:
        if self._on_status_changed is not None:
            self._on_status_changed(status, detail)

    def _emit_error(self, message: str) -> None:
        if self._on_error is not None:
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
