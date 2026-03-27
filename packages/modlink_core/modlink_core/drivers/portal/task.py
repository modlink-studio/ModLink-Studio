from __future__ import annotations

from collections.abc import Callable
from threading import Event

from modlink_sdk.signals import Signal


class DriverTask:
    """Observable one-shot task for driver operations."""

    def __init__(
        self,
        *,
        request: object | None = None,
        parent: object | None = None,
    ) -> None:
        self._request = request
        self._state = "running"
        self._result: object | None = None
        self._error: Exception | None = None
        self._done_event = Event()
        self._parent = parent
        self.sig_done = Signal()

    @property
    def request(self) -> object | None:
        return self._request

    @property
    def state(self) -> str:
        return self._state

    @property
    def is_running(self) -> bool:
        return self._state == "running"

    @property
    def is_finished(self) -> bool:
        return self._state == "finished"

    @property
    def is_failed(self) -> bool:
        return self._state == "failed"

    @property
    def result(self) -> object | None:
        return self._result

    @property
    def error(self) -> Exception | None:
        return self._error

    def add_done_callback(self, callback: Callable[[DriverTask], None]) -> None:
        if not callable(callback):
            raise TypeError("task callback must be callable")
        if self._done_event.is_set():
            callback(self)
            return
        self.sig_done.connect(lambda: callback(self))

    def wait(self, timeout: float | None = None) -> bool:
        return self._done_event.wait(timeout)

    def deleteLater(self) -> None:  # noqa: N802 - Qt compatibility shim
        return

    def _finish(self, result: object) -> None:
        if self._state != "running":
            return
        self._result = result
        self._state = "finished"
        self._done_event.set()
        self.sig_done.emit()

    def _fail(self, error: Exception) -> None:
        if self._state != "running":
            return
        self._error = error
        self._state = "failed"
        self._done_event.set()
        self.sig_done.emit()
