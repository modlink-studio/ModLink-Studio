from __future__ import annotations

import threading
import time
import unittest
from concurrent.futures import Future

import pytest

QtCore = pytest.importorskip("PyQt6.QtCore")
QThread = QtCore.QThread
QtWidgets = pytest.importorskip("PyQt6.QtWidgets")
QApplication = QtWidgets.QApplication

from modlink_ui.bridge import QtDriverTask


class QtDriverTaskTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def test_already_completed_future_runs_refresh_then_callback_once(self) -> None:
        future: Future[object | None] = Future()
        future.set_result(["demo"])
        calls: list[str] = []

        task = QtDriverTask(
            future,
            action="search",
            on_completed=lambda: calls.append("refresh"),
        )
        task.add_done_callback(lambda _task: calls.append("callback"))

        self.assertEqual([], calls)

        self._pump_events_until(lambda: calls == ["refresh", "callback"])

        self.assertEqual(["refresh", "callback"], calls)
        self.assertEqual("finished", task.state)
        self.assertEqual(["demo"], task.result)

        self._app.processEvents()
        self.assertEqual(["refresh", "callback"], calls)
        task.deleteLater()
        self._app.processEvents()

    def test_done_callback_runs_on_qt_thread(self) -> None:
        future: Future[object | None] = Future()
        callback_threads: list[bool] = []

        task = QtDriverTask(future, action="connect_device")
        task.add_done_callback(
            lambda done_task: callback_threads.append(QThread.currentThread() == done_task.thread())
        )

        threading.Thread(target=lambda: future.set_result(None), daemon=True).start()

        self._pump_events_until(lambda: len(callback_threads) == 1)

        self.assertEqual([True], callback_threads)
        self.assertEqual("finished", task.state)
        task.deleteLater()
        self._app.processEvents()

    def _pump_events_until(self, predicate, *, timeout: float = 1.0) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            self._app.processEvents()
            if predicate():
                return
            time.sleep(0.01)
        self._app.processEvents()
        if predicate():
            return
        raise AssertionError("condition not reached before timeout")


if __name__ == "__main__":
    unittest.main()
