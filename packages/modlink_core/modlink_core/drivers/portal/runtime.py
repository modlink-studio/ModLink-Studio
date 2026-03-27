from __future__ import annotations

from uuid import uuid4

from modlink_qt import QObject, QThread, Qt, pyqtSignal, pyqtSlot

from modlink_sdk import Driver, DriverFactory, FrameEnvelope, SearchResult, StreamDescriptor

from .invoker import DriverInvoker
from .task import DriverTask


class DriverRuntime(QObject):
    sig_error = pyqtSignal(str)
    sig_frame = pyqtSignal(FrameEnvelope)
    sig_connection_lost = pyqtSignal(object)

    _request_call = pyqtSignal(str, object)

    def __init__(
        self,
        driver_factory: DriverFactory,
        *,
        thread_name: str | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self._driver = self._create_driver(driver_factory)
        self._driver_id = self._driver.device_id
        self._display_name = self._driver.display_name
        self._supported_providers = tuple(
            provider
            for provider in (
                str(item).strip() for item in self._driver.supported_providers
            )
            if provider
        )
        self._thread = QThread(self)
        self._thread.setObjectName(
            thread_name or f"modlink.driver.{self._driver_id.strip()}"
        )
        self._running = False
        self._pending_tasks: dict[str, DriverTask] = {}
        self._invoker = DriverInvoker(self._driver)

        self._driver.moveToThread(self._thread)
        self._driver.sig_frame.connect(self.sig_frame.emit)
        self._driver.sig_connection_lost.connect(self.sig_connection_lost.emit)

        self._invoker.moveToThread(self._thread)
        self._request_call.connect(
            self._invoker.handle_call,
            Qt.ConnectionType.QueuedConnection,
        )
        self._invoker.sig_task_done.connect(self._on_task_done)

        self._thread.started.connect(self._on_thread_started)
        self._thread.finished.connect(self._on_thread_finished)
        self._thread.finished.connect(self._driver.deleteLater)
        self._thread.finished.connect(self._invoker.deleteLater)

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
        return self._running and self._thread.isRunning()

    def descriptors(self) -> list[StreamDescriptor]:
        return self._driver.descriptors()

    def start(self) -> None:
        if self._thread.isRunning():
            return
        self._thread.start()

    def stop(self, *, timeout_ms: int = 3000) -> None:
        if not self._thread.isRunning():
            self._running = False
            return

        self._request_call.emit("shutdown", None)
        self._thread.quit()
        if not self._thread.wait(timeout_ms):
            self.sig_error.emit(
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
        task = DriverTask(request=request, parent=self)
        self._pending_tasks[task_id] = task
        self._request_call.emit(action, (task_id, request))
        return task

    @pyqtSlot()
    def _on_thread_started(self) -> None:
        self._running = True
        self._request_call.emit("on_thread_started", None)

    @pyqtSlot()
    def _on_thread_finished(self) -> None:
        self._running = False
        self._fail_pending_tasks(
            RuntimeError(
                "driver thread stopped before pending tasks completed: "
                f"driver_id={self.driver_id}"
            )
        )

    @pyqtSlot(str, str, object, object)
    def _on_task_done(
        self, task_id: str, action: str, result: object, error: object
    ) -> None:
        task = self._pending_tasks.pop(task_id, None)
        if task is None:
            return
        if error is not None:
            exception = self._coerce_exception(error)
            task._fail(exception)
            self.sig_error.emit(
                f"DRIVER_CALL_FAILED: driver_id={self.driver_id}: "
                f"action={action}: {type(exception).__name__}: {exception}"
            )
            return
        task._finish(result)

    def _fail_pending_tasks(self, error: Exception) -> None:
        pending = list(self._pending_tasks.values())
        self._pending_tasks.clear()
        for task in pending:
            task._fail(RuntimeError(str(error)))

    @staticmethod
    def _coerce_exception(error: object) -> Exception:
        if isinstance(error, Exception):
            return error
        return RuntimeError(str(error))

    @staticmethod
    def _create_driver(driver_factory: DriverFactory) -> Driver:
        if not callable(driver_factory):
            raise TypeError("driver_factory must be callable")

        driver = driver_factory()
        if not isinstance(driver, Driver):
            raise TypeError("driver_factory must return a Driver instance")
        if driver.parent() is not None:
            raise ValueError(
                "driver must not have a QObject parent before attaching to a portal"
            )
        driver_id = driver.device_id.strip()
        if not driver_id:
            raise ValueError("driver.device_id must not be empty")
        return driver
