from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import CancelledError, Future
from threading import Event, RLock
from uuid import uuid4

from PyQt6.QtCore import QObject, Qt, pyqtSignal, pyqtSlot

from modlink_core.drivers import DriverPortal
from modlink_core.models import DriverSnapshot
from modlink_sdk import SearchResult, StreamDescriptor


class QtDriverTask(QObject):
    _sig_finalize_requested = pyqtSignal()
    _sig_invoke_callback_requested = pyqtSignal(object)

    def __init__(
        self,
        future: Future[object | None],
        *,
        action: str,
        request: object | None = None,
        on_completed: Callable[[], None] | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self._future = future
        self._on_completed = on_completed
        self._done = Event()
        self._lock = RLock()
        self._callbacks: list[Callable[[QtDriverTask], None]] = []
        self._finalized = False

        self.task_id = uuid4().hex
        self.action = action
        self.request = request
        self.result: object | None = None
        self.error: Exception | None = None
        self.state = "running"

        self._sig_finalize_requested.connect(
            self._finalize_on_qt_thread,
            Qt.ConnectionType.QueuedConnection,
        )
        self._sig_invoke_callback_requested.connect(
            self._invoke_callback_on_qt_thread,
            Qt.ConnectionType.QueuedConnection,
        )

        if future.done():
            self._sig_finalize_requested.emit()
            return

        future.add_done_callback(lambda _future: self._sig_finalize_requested.emit())

    @property
    def is_running(self) -> bool:
        return self.state == "running"

    def wait(self, timeout: float | None = None) -> bool:
        return self._done.wait(timeout)

    def add_done_callback(self, callback: Callable[[QtDriverTask], None]) -> None:
        with self._lock:
            if self._finalized:
                invoke_later = True
            else:
                invoke_later = False
                self._callbacks.append(callback)
        if invoke_later:
            self._sig_invoke_callback_requested.emit(callback)

    @pyqtSlot()
    def _finalize_on_qt_thread(self) -> None:
        with self._lock:
            if self._finalized:
                return
            self._sync_from_future()
            self._done.set()
            self._finalized = True
            callbacks = list(self._callbacks)
            self._callbacks.clear()

        if self._on_completed is not None:
            self._on_completed()
        for callback in callbacks:
            callback(self)

    @pyqtSlot(object)
    def _invoke_callback_on_qt_thread(self, callback: object) -> None:
        if callable(callback):
            callback(self)

    def _sync_from_future(self) -> None:
        if not self._future.done():
            self.state = "running"
            return
        if self._future.cancelled():
            self.result = None
            self.error = CancelledError()
            self.state = "failed"
            return

        error = self._future.exception()
        if error is not None:
            self.result = None
            self.error = error
            self.state = "failed"
            return

        self.result = self._future.result()
        self.error = None
        self.state = "finished"


class QtDriverPortal(QObject):
    sig_state_changed = pyqtSignal(object)
    sig_connection_lost = pyqtSignal(object)
    sig_error = pyqtSignal(str)

    def __init__(
        self,
        backend_portal: DriverPortal,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self._backend_portal = backend_portal
        self._snapshot = backend_portal.snapshot()

    @property
    def driver_id(self) -> str:
        return self._snapshot.driver_id

    @property
    def display_name(self) -> str:
        return self._snapshot.display_name

    @property
    def supported_providers(self) -> tuple[str, ...]:
        return self._snapshot.supported_providers

    @property
    def is_running(self) -> bool:
        return self._snapshot.is_running

    @property
    def is_connected(self) -> bool:
        return self._snapshot.is_connected

    @property
    def is_streaming(self) -> bool:
        return self._snapshot.is_streaming

    @property
    def state(self) -> DriverSnapshot:
        return self._snapshot

    def snapshot(self) -> DriverSnapshot:
        return self._snapshot

    def descriptors(self) -> list[StreamDescriptor]:
        return self._backend_portal.descriptors()

    def resync_from_backend(self) -> None:
        self._apply_snapshot(self._backend_portal.snapshot())

    def handle_connection_lost(self, detail: object | None) -> None:
        self.resync_from_backend()
        self._emit_connection_lost(detail)

    def handle_executor_failed(self, detail: object) -> None:
        self._emit_error(str(detail))

    def search(self, provider: str) -> QtDriverTask:
        return self._wrap_task(
            self._backend_portal.search(provider),
            action="search",
            request=provider,
        )

    def connect_device(self, config: SearchResult) -> QtDriverTask:
        return self._wrap_task(
            self._backend_portal.connect_device(config),
            action="connect_device",
            request=config,
            refresh_snapshot=True,
        )

    def disconnect_device(self) -> QtDriverTask:
        return self._wrap_task(
            self._backend_portal.disconnect_device(),
            action="disconnect_device",
            refresh_snapshot=True,
        )

    def start_streaming(self) -> QtDriverTask:
        return self._wrap_task(
            self._backend_portal.start_streaming(),
            action="start_streaming",
            refresh_snapshot=True,
        )

    def stop_streaming(self) -> QtDriverTask:
        return self._wrap_task(
            self._backend_portal.stop_streaming(),
            action="stop_streaming",
            refresh_snapshot=True,
        )

    def _apply_snapshot(self, snapshot: DriverSnapshot) -> None:
        self._snapshot = snapshot
        self.sig_state_changed.emit(snapshot)

    def _emit_error(self, message: str) -> None:
        self.sig_error.emit(message)

    def _emit_connection_lost(self, detail: object | None) -> None:
        self.sig_connection_lost.emit(detail)

    def _refresh_snapshot(self) -> None:
        self.resync_from_backend()

    def _wrap_task(
        self,
        future: Future[object | None],
        *,
        action: str,
        request: object | None = None,
        refresh_snapshot: bool = False,
    ) -> QtDriverTask:
        return QtDriverTask(
            future,
            action=action,
            request=request,
            on_completed=self.resync_from_backend if refresh_snapshot else None,
            parent=self,
        )
