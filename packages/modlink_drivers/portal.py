from __future__ import annotations

import time
from dataclasses import dataclass

from PyQt6.QtCore import QObject, QThread, Qt, pyqtBoundSignal, pyqtSignal

from packages.modlink_shared import StreamDescriptor

from .base import Driver, DriverFactory


@dataclass(slots=True)
class DriverEvent:
    driver_id: str
    event: object
    ts: float


class DriverPortal(QObject):
    """Public driver-facing gateway used by the rest of the system.

    The portal owns driver instantiation, thread hosting, and cross-thread requests.
    Other modules interact with the portal instead of the raw driver.
    """

    sig_event = pyqtSignal(object)
    sig_error = pyqtSignal(str)

    _request_on_thread_started = pyqtSignal()
    _request_shutdown = pyqtSignal()
    _request_search = pyqtSignal(object)
    _request_connect = pyqtSignal(object)
    _request_disconnect = pyqtSignal()
    _request_start_streaming = pyqtSignal()
    _request_stop_streaming = pyqtSignal()

    def __init__(
        self,
        driver_factory: DriverFactory,
        *,
        thread_name: str | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self._driver = self._create_driver(driver_factory)
        driver_id = self._driver.device_id.strip()
        if not driver_id:
            raise ValueError("driver.device_id must not be empty")

        self._driver_id = self._driver.device_id
        self._display_name = self._driver.display_name
        self._thread = QThread(self)
        self._thread.setObjectName(
            thread_name or f"modlink.driver.{driver_id}"
        )
        self._running = False

        self._driver.moveToThread(self._thread)
        self._driver.sig_event.connect(self._forward_event)

        self._request_on_thread_started.connect(
            self._driver.on_thread_started,
            Qt.ConnectionType.QueuedConnection,
        )
        self._request_shutdown.connect(
            self._driver.shutdown,
            Qt.ConnectionType.QueuedConnection,
        )
        self._request_search.connect(
            self._driver.search,
            Qt.ConnectionType.QueuedConnection,
        )
        self._request_connect.connect(
            self._driver.connect_device,
            Qt.ConnectionType.QueuedConnection,
        )
        self._request_disconnect.connect(
            self._driver.disconnect_device,
            Qt.ConnectionType.QueuedConnection,
        )
        self._request_start_streaming.connect(
            self._driver.start_streaming,
            Qt.ConnectionType.QueuedConnection,
        )
        self._request_stop_streaming.connect(
            self._driver.stop_streaming,
            Qt.ConnectionType.QueuedConnection,
        )

        self._thread.started.connect(self._on_thread_started)
        self._thread.finished.connect(self._on_thread_finished)

    @property
    def driver_id(self) -> str:
        return self._driver_id

    @property
    def display_name(self) -> str:
        return self._display_name

    @property
    def is_running(self) -> bool:
        return self._running and self._thread.isRunning()

    def streams(self) -> list[tuple[StreamDescriptor, pyqtBoundSignal]]:
        return self._driver.streams()

    def start(self) -> None:
        if self._thread.isRunning():
            return
        self._thread.start()

    def stop(self, *, timeout_ms: int = 3000) -> None:
        if not self._thread.isRunning():
            self._running = False
            return

        self._request_shutdown.emit()
        self._thread.quit()
        if not self._thread.wait(timeout_ms):
            self.sig_error.emit(
                f"DRIVER_STOP_TIMEOUT: driver_id={self.driver_id}: timeout_ms={timeout_ms}"
            )

    def search(self, request: object | None = None) -> None:
        self._request_search.emit(request)

    def connect_device(self, config: object | None = None) -> None:
        self._request_connect.emit(config)

    def disconnect_device(self) -> None:
        self._request_disconnect.emit()

    def start_streaming(self) -> None:
        self._request_start_streaming.emit()

    def stop_streaming(self) -> None:
        self._request_stop_streaming.emit()

    def _forward_event(self, event: object) -> None:
        self.sig_event.emit(
            DriverEvent(driver_id=self.driver_id, event=event, ts=time.time())
        )

    def _on_thread_started(self) -> None:
        self._running = True
        self._request_on_thread_started.emit()

    def _on_thread_finished(self) -> None:
        self._running = False

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
        return driver
