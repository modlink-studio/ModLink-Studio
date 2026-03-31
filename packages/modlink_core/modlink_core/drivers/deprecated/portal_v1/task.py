from __future__ import annotations

from threading import Event


class DriverTask:
    """Passive one-shot task handle for driver operations."""

    def __init__(
        self,
        *,
        task_id: str,
        action: str,
        request: object | None = None,
        parent: object | None = None,
    ) -> None:
        self._task_id = task_id
        self._action = action
        self._request = request
        self._state = "running"
        self._result: object | None = None
        self._error: Exception | None = None
        self._done_event = Event()
        self._parent = parent

    @property
    def task_id(self) -> str:
        return self._task_id

    @property
    def action(self) -> str:
        return self._action

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

    def _fail(self, error: Exception) -> None:
        if self._state != "running":
            return
        self._error = error
        self._state = "failed"
        self._done_event.set()
