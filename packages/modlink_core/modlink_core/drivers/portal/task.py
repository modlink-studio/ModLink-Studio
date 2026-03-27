from __future__ import annotations

from modlink_qt import QObject, pyqtSignal


class DriverTask(QObject):
    """Observable one-shot task for driver operations."""

    sig_done = pyqtSignal()

    def __init__(
        self,
        *,
        request: object | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self._request = request
        self._state = "running"
        self._result: object | None = None
        self._error: Exception | None = None

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

    def _finish(self, result: object) -> None:
        if self._state != "running":
            return
        self._result = result
        self._state = "finished"
        self.sig_done.emit()

    def _fail(self, error: Exception) -> None:
        if self._state != "running":
            return
        self._error = error
        self._state = "failed"
        self.sig_done.emit()
