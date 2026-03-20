from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from modlink_sdk import Driver


class DriverInvoker(QObject):
    """Runs driver calls on the driver thread and relays outcomes back to the runtime."""

    sig_task_done = pyqtSignal(str, str, object, object)

    def __init__(self, driver: Driver) -> None:
        super().__init__()
        self._driver = driver

    @pyqtSlot(str, object)
    def handle_call(self, action: str, payload: object) -> None:
        if action == "on_thread_started":
            self._driver.on_thread_started()
            return
        if action == "shutdown":
            self._driver.shutdown()
            return

        task_id, request = self._unpack_task_payload(payload)
        
        if action == "search":
            provider, search_request = self._unpack_search_request(request)
            self._run_task(task_id, action, self._driver.search, provider, search_request)
            return
        if action == "connect_device":
            self._run_task(task_id, action, self._driver.connect_device, request)
            return
        if action == "disconnect_device":
            self._run_task(task_id, action, self._driver.disconnect_device)
            return
        if action == "start_streaming":
            self._run_task(task_id, action, self._driver.start_streaming)
            return
        if action == "stop_streaming":
            self._run_task(task_id, action, self._driver.stop_streaming)
            return

        self.sig_task_done.emit(
            task_id,
            action,
            None,
            RuntimeError(f"unknown driver action: {action}"),
        )

    def _run_task(self, task_id: str, action: str, func, *args: object) -> None:
        result = None
        error = None
        try:
            result = func(*args)
        except Exception as exc:
            error = exc
        self.sig_task_done.emit(task_id, action, result, error)

    @staticmethod
    def _unpack_task_payload(payload: object) -> tuple[str, object | None]:
        if not isinstance(payload, tuple) or len(payload) != 2:
            raise TypeError("task payload must be a (task_id, request) tuple")
        task_id, request = payload
        if not isinstance(task_id, str) or not task_id:
            raise TypeError("task payload task_id must be a non-empty string")
        return task_id, request

    @staticmethod
    def _unpack_search_request(request: object) -> tuple[str, object | None]:
        if not isinstance(request, dict):
            raise TypeError("search request must be a dict")
        provider = request.get("provider")
        if not isinstance(provider, str) or not provider.strip():
            raise TypeError("search request provider must be a non-empty string")
        return provider, request.get("request")
