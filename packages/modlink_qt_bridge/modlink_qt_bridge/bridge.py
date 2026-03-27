from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from threading import Event, RLock

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from modlink_core.acquisition.backend import ACQUISITION_ROOT_DIR_KEY, AcquisitionBackend
from modlink_core.drivers import DriverPortal, DriverTask
from modlink_core.events import (
    AcquisitionErrorEvent,
    AcquisitionLifecycleEvent,
    AcquisitionSnapshot,
    AcquisitionStateChangedEvent,
    BackendErrorEvent,
    DriverSnapshot,
    DriverStateChangedEvent,
    DriverTaskFinishedEvent,
    FrameArrivedEvent,
    SettingChangedEvent,
    StreamDescriptorRegisteredEvent,
)
from modlink_core.runtime.engine import ModLinkEngine
from modlink_core.settings.service import SettingsService
from modlink_sdk import FrameEnvelope, SearchResult, StreamDescriptor


class QtDriverTask(QObject):
    sig_done = pyqtSignal()

    def __init__(
        self,
        backend_task: DriverTask,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self._backend_task = backend_task
        self._done = Event()
        self._lock = RLock()
        self._callbacks: list[Callable[[QtDriverTask], None]] = []
        self._signal_emitted = False

        self.task_id = backend_task.task_id
        self.action = backend_task.action
        self.request = backend_task.request
        self.result = backend_task.result
        self.error = backend_task.error
        self.state = backend_task.state

        backend_task.add_done_callback(self._on_backend_task_done)

    @property
    def is_running(self) -> bool:
        return self.state == "running"

    def wait(self, timeout: float | None = None) -> bool:
        return self._done.wait(timeout)

    def add_done_callback(self, callback: Callable[[QtDriverTask], None]) -> None:
        with self._lock:
            if self._signal_emitted:
                callback(self)
                return
            self._callbacks.append(callback)

    def _on_backend_task_done(self, task: DriverTask) -> None:
        with self._lock:
            self._sync_from_backend(task)
            self._done.set()

    def complete_from_event(self, event: DriverTaskFinishedEvent) -> None:
        del event
        with self._lock:
            self._sync_from_backend(self._backend_task)
            self._done.set()
            if self._signal_emitted:
                return
            self._signal_emitted = True
            callbacks = list(self._callbacks)
            self._callbacks.clear()

        for callback in callbacks:
            callback(self)
        self.sig_done.emit()

    def _sync_from_backend(self, task: DriverTask) -> None:
        self.request = task.request
        self.result = task.result
        self.error = task.error
        self.state = task.state


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
        self._tasks: dict[str, QtDriverTask] = {}

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

    def search(self, provider: str) -> QtDriverTask:
        return self._wrap_task(self._backend_portal.search(provider))

    def connect_device(self, config: SearchResult) -> QtDriverTask:
        return self._wrap_task(self._backend_portal.connect_device(config))

    def disconnect_device(self) -> QtDriverTask:
        return self._wrap_task(self._backend_portal.disconnect_device())

    def start_streaming(self) -> QtDriverTask:
        return self._wrap_task(self._backend_portal.start_streaming())

    def stop_streaming(self) -> QtDriverTask:
        return self._wrap_task(self._backend_portal.stop_streaming())

    def _apply_snapshot(self, event: DriverStateChangedEvent) -> None:
        previous = self._snapshot
        self._snapshot = event.snapshot
        self.sig_state_changed.emit(event.snapshot)
        if (
            event.snapshot.status == "connection_lost"
            and (
                previous.status != "connection_lost"
                or previous.status_detail != event.snapshot.status_detail
            )
        ):
            self.sig_connection_lost.emit(event.snapshot.status_detail)

    def _complete_task(self, event: DriverTaskFinishedEvent) -> None:
        task = self._tasks.pop(event.task_id, None)
        if task is None:
            return
        task.complete_from_event(event)

    def _emit_error(self, message: str) -> None:
        self.sig_error.emit(message)

    def _wrap_task(self, backend_task: DriverTask) -> QtDriverTask:
        task = QtDriverTask(backend_task, parent=self)
        self._tasks[task.task_id] = task
        return task


class QtBusBridge(QObject):
    sig_stream_descriptor = pyqtSignal(object)
    sig_frame = pyqtSignal(object)
    sig_error = pyqtSignal(str)

    def __init__(self, engine: ModLinkEngine, parent: QObject | None = None) -> None:
        super().__init__(parent=parent)
        self._engine = engine
        self._descriptors = engine.bus.descriptors()

    def descriptors(self) -> dict[str, StreamDescriptor]:
        return dict(self._descriptors)

    def descriptor(self, stream_id: str) -> StreamDescriptor | None:
        return self._descriptors.get(stream_id)

    def _register_descriptor(self, event: StreamDescriptorRegisteredEvent) -> None:
        self._descriptors[event.descriptor.stream_id] = event.descriptor
        self.sig_stream_descriptor.emit(event.descriptor)

    def _emit_frame(self, frame: FrameEnvelope) -> None:
        self.sig_frame.emit(frame)

    def _emit_error(self, message: str) -> None:
        self.sig_error.emit(message)


class QtSettingsBridge(QObject):
    sig_setting_changed = pyqtSignal(object)

    def __init__(
        self,
        settings: SettingsService,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self._settings = settings

    def get(self, key: str, default: object | None = None) -> object | None:
        return self._settings.get(key, default)

    def set(self, key: str, value: object, *, persist: bool = True) -> None:
        self._settings.set(key, value, persist=persist)

    def remove(self, key: str, *, persist: bool = True) -> None:
        self._settings.remove(key, persist=persist)

    def snapshot(self) -> dict[str, object]:
        return self._settings.snapshot()

    def _emit_setting_changed(self, event: SettingChangedEvent) -> None:
        self.sig_setting_changed.emit(event)


class QtAcquisitionBridge(QObject):
    sig_state_changed = pyqtSignal(str)
    sig_error = pyqtSignal(str)
    sig_event = pyqtSignal(object)

    def __init__(
        self,
        backend: AcquisitionBackend,
        settings: QtSettingsBridge,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self._backend = backend
        self._settings = settings
        self._snapshot = backend.snapshot()

    @property
    def root_dir(self) -> Path:
        configured = self._settings.get(ACQUISITION_ROOT_DIR_KEY)
        resolved = configured or self._snapshot.root_dir
        return Path(str(resolved))

    @property
    def state(self) -> str:
        return self._snapshot.state

    @property
    def is_started(self) -> bool:
        return self._snapshot.is_started

    @property
    def is_recording(self) -> bool:
        return self._snapshot.is_recording

    def snapshot(self) -> AcquisitionSnapshot:
        return self._snapshot

    def start_recording(
        self,
        session_name: str,
        recording_label: str | None = None,
    ) -> None:
        self._backend.start_recording(session_name, recording_label)

    def stop_recording(self) -> None:
        self._backend.stop_recording()

    def add_marker(self, label: str | None = None) -> None:
        self._backend.add_marker(label)

    def add_segment(
        self,
        start_ns: int,
        end_ns: int,
        label: str | None = None,
    ) -> None:
        self._backend.add_segment(start_ns=start_ns, end_ns=end_ns, label=label)

    def _apply_state(self, event: AcquisitionStateChangedEvent) -> None:
        self._snapshot = event.snapshot
        self.sig_state_changed.emit(event.snapshot.state)

    def _emit_error(self, event: AcquisitionErrorEvent) -> None:
        self.sig_error.emit(event.message)

    def _emit_lifecycle(self, event: AcquisitionLifecycleEvent) -> None:
        self.sig_event.emit(event)


class QtModLinkBridge(QObject):
    def __init__(
        self,
        engine: ModLinkEngine,
        *,
        interval_ms: int = 16,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self._engine = engine
        self._settings_service = SettingsService.instance()
        self.settings = QtSettingsBridge(self._settings_service, parent=self)
        self.bus = QtBusBridge(engine, parent=self)
        self.acquisition = QtAcquisitionBridge(
            engine.acquisition,
            self.settings,
            parent=self,
        )
        self._driver_portals = {
            portal.driver_id: QtDriverPortal(portal, parent=self)
            for portal in engine.driver_portals()
        }
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._drain_events)
        self._timer.start(max(1, int(interval_ms)))

    def driver_portals(self) -> tuple[QtDriverPortal, ...]:
        return tuple(self._driver_portals.values())

    def driver_portal(self, driver_id: str) -> QtDriverPortal | None:
        return self._driver_portals.get(driver_id)

    def shutdown(self) -> None:
        if self._timer.isActive():
            self._timer.stop()
        self._engine.shutdown()

    def _drain_events(self) -> None:
        events = self._engine.drain_events()
        if not events:
            return

        frames_by_stream: dict[str, FrameEnvelope] = {}
        for event in events:
            if isinstance(event, FrameArrivedEvent):
                frames_by_stream[event.frame.stream_id] = event.frame
                continue

            if isinstance(event, StreamDescriptorRegisteredEvent):
                self.bus._register_descriptor(event)
                continue

            if isinstance(event, DriverStateChangedEvent):
                portal = self._driver_portals.get(event.snapshot.driver_id)
                if portal is not None:
                    portal._apply_snapshot(event)
                continue

            if isinstance(event, DriverTaskFinishedEvent):
                portal = self._driver_portals.get(event.driver_id)
                if portal is not None:
                    portal._complete_task(event)
                continue

            if isinstance(event, AcquisitionStateChangedEvent):
                self.acquisition._apply_state(event)
                continue

            if isinstance(event, AcquisitionErrorEvent):
                self.acquisition._emit_error(event)
                continue

            if isinstance(event, AcquisitionLifecycleEvent):
                self.acquisition._emit_lifecycle(event)
                continue

            if isinstance(event, SettingChangedEvent):
                self.settings._emit_setting_changed(event)
                continue

            if isinstance(event, BackendErrorEvent):
                self._dispatch_backend_error(event)

        for frame in frames_by_stream.values():
            self.bus._emit_frame(frame)

    def _dispatch_backend_error(self, event: BackendErrorEvent) -> None:
        if event.source == "stream_bus":
            self.bus._emit_error(event.message)
            return

        if event.source.startswith("driver:"):
            driver_id = event.source.removeprefix("driver:")
            portal = self._driver_portals.get(driver_id)
            if portal is not None:
                portal._emit_error(event.message)
