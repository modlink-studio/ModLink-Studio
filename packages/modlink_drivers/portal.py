from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Protocol

from PyQt6.QtCore import QObject, QThread, Qt, pyqtSignal

from packages.modlink_shared import FrameSignal, StreamDescriptor

from .base import Driver


class StreamRegistry(Protocol):
    def register_stream(
        self,
        descriptor: StreamDescriptor,
        frame_signal: FrameSignal,
    ) -> None: ...


@dataclass(slots=True)
class DriverEvent:
    driver_id: str
    event: object
    ts: float


class DriverPortal(QObject):
    """Public driver-facing gateway used by the rest of the system.

    The portal owns thread hosting, stream registration, and cross-thread
    requests. Other modules interact with the portal instead of the raw driver.
    """

    sig_event = pyqtSignal(object)
    sig_started = pyqtSignal(str)
    sig_stopped = pyqtSignal(str)
    sig_error = pyqtSignal(str)

    _request_bootstrap = pyqtSignal()
    _request_shutdown = pyqtSignal()
    _request_search = pyqtSignal(object)
    _request_connect = pyqtSignal(object)
    _request_disconnect = pyqtSignal()
    _request_start_streaming = pyqtSignal()
    _request_stop_streaming = pyqtSignal()

    def __init__(
        self,
        driver: Driver,
        stream_registry: StreamRegistry,
        *,
        auto_bootstrap: bool = True,
        thread_name: str | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent=parent)
        if driver.parent() is not None:
            raise ValueError(
                "driver must not have a QObject parent before attaching to a portal"
            )

        self._driver = driver
        self._stream_registry = stream_registry
        self._auto_bootstrap = auto_bootstrap
        self._thread = QThread(self)
        self._thread.setObjectName(
            thread_name or f"modlink.driver.{self.driver_id or 'unnamed'}"
        )
        self._streams_registered = False
        self._running = False

        self._driver.moveToThread(self._thread)
        self._driver.sig_event.connect(self._forward_event)

        self._request_bootstrap.connect(
            self._driver.bootstrap,
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
        return self._driver.device_id

    @property
    def display_name(self) -> str:
        return self._driver.display_name

    @property
    def is_running(self) -> bool:
        return self._running and self._thread.isRunning()

    def start(self) -> None:
        if self._thread.isRunning():
            return
        try:
            self._register_streams()
        except ValueError as exc:
            self.sig_error.emit(
                f"DRIVER_REGISTER_FAILED: driver_id={self.driver_id}: {exc}"
            )
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

    def _register_streams(self) -> None:
        if self._streams_registered:
            return

        for descriptor in self._driver.stream_descriptors():
            self._stream_registry.register_stream(
                descriptor,
                self._driver.frame_signal(descriptor.stream_id),
            )

        self._streams_registered = True

    def _forward_event(self, event: object) -> None:
        self.sig_event.emit(
            DriverEvent(driver_id=self.driver_id, event=event, ts=time.time())
        )

    def _on_thread_started(self) -> None:
        self._running = True
        self.sig_started.emit(self.driver_id)
        if self._auto_bootstrap:
            self._request_bootstrap.emit()

    def _on_thread_finished(self) -> None:
        self._running = False
        self.sig_stopped.emit(self.driver_id)
