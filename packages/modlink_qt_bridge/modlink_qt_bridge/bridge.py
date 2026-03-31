from __future__ import annotations

from concurrent.futures import CancelledError, Future
from collections.abc import Callable, Iterable
from pathlib import Path
from threading import Event, RLock, Thread
import time
from uuid import uuid4

from PyQt6.QtCore import QObject, pyqtSignal

from modlink_core.acquisition.backend import ACQUISITION_ROOT_DIR_KEY, AcquisitionBackend
from modlink_core.bus import FrameStream, StreamBus
from modlink_core.drivers import DriverPortal
from modlink_core.events import (
    AcquisitionErrorEvent,
    AcquisitionLifecycleEvent,
    AcquisitionSnapshot,
    AcquisitionStateChangedEvent,
    BackendErrorEvent,
    DriverConnectionLostEvent,
    DriverSnapshot,
    EventStream,
    SettingChangedEvent,
    StreamClosedError,
)
from modlink_core.runtime.engine import ModLinkEngine
from modlink_core.settings.service import SettingsService
from modlink_sdk import FrameEnvelope, SearchResult, StreamDescriptor


class QtDriverTask(QObject):
    sig_done = pyqtSignal()

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
        self._signal_emitted = False

        self.task_id = uuid4().hex
        self.action = action
        self.request = request
        self.result: object | None = None
        self.error: Exception | None = None
        self.state = "running"

        if future.done():
            self.complete_from_future()
            return

        future.add_done_callback(lambda _future: self.complete_from_future())

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

    def complete_from_future(self) -> None:
        with self._lock:
            self._sync_from_future()
            self._done.set()
            if self._signal_emitted:
                return
            self._signal_emitted = True
            callbacks = list(self._callbacks)
            self._callbacks.clear()

        if self._on_completed is not None:
            self._on_completed()
        for callback in callbacks:
            callback(self)
        self.sig_done.emit()

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
        self._apply_snapshot(self._backend_portal.snapshot())

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
            on_completed=self._refresh_snapshot if refresh_snapshot else None,
            parent=self,
        )


class QtBusBridge(QObject):
    sig_frames = pyqtSignal(object)
    sig_frame = pyqtSignal(object)
    sig_error = pyqtSignal(str)

    def __init__(self, bus: StreamBus, parent: QObject | None = None) -> None:
        super().__init__(parent=parent)
        self._bus = bus
        self._descriptors = bus.descriptors()

    def descriptors(self) -> dict[str, StreamDescriptor]:
        return dict(self._descriptors)

    def descriptor(self, stream_id: str) -> StreamDescriptor | None:
        return self._descriptors.get(stream_id)

    def _emit_frames(self, frames: list[FrameEnvelope]) -> None:
        if not frames:
            return
        self.sig_frames.emit(frames)
        for frame in frames:
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

    def _resync_snapshot(self, snapshot: dict[str, object]) -> None:
        for key, value in _flatten_settings(snapshot):
            self.sig_setting_changed.emit(
                SettingChangedEvent(key=key, value=value, ts=time.time())
            )


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

    def _apply_snapshot(self, snapshot: AcquisitionSnapshot) -> None:
        self._snapshot = snapshot
        self.sig_state_changed.emit(snapshot.state)

    def _emit_error(self, event: AcquisitionErrorEvent) -> None:
        self.sig_error.emit(event.message)

    def _emit_lifecycle(self, event: AcquisitionLifecycleEvent) -> None:
        self.sig_event.emit(event)


class QtModLinkBridge(QObject):
    def __init__(
        self,
        engine: ModLinkEngine,
        *,
        event_stream_maxsize: int = 1024,
        frame_stream_maxsize: int = 256,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self._engine = engine
        self._stop_event = Event()
        self._event_stream: EventStream = engine.open_event_stream(
            maxsize=event_stream_maxsize
        )
        self._frame_stream: FrameStream = engine.bus.open_frame_stream(
            maxsize=frame_stream_maxsize,
            drop_policy="drop_oldest",
            consumer_name="qt_bridge",
        )
        self.settings = QtSettingsBridge(engine.settings, parent=self)
        self.bus = QtBusBridge(engine.bus, parent=self)
        self.acquisition = QtAcquisitionBridge(
            engine.acquisition,
            self.settings,
            parent=self,
        )
        self._driver_portals = {
            portal.driver_id: QtDriverPortal(portal, parent=self)
            for portal in engine.driver_portals()
        }
        self._event_thread = Thread(
            target=self._run_event_pump,
            name="modlink.qt_bridge.events",
            daemon=True,
        )
        self._frame_thread = Thread(
            target=self._run_frame_pump,
            name="modlink.qt_bridge.frames",
            daemon=True,
        )
        self._event_thread.start()
        self._frame_thread.start()

    def driver_portals(self) -> tuple[QtDriverPortal, ...]:
        return tuple(self._driver_portals.values())

    def driver_portal(self, driver_id: str) -> QtDriverPortal | None:
        return self._driver_portals.get(driver_id)

    def shutdown(self) -> None:
        self._stop_event.set()
        self._event_stream.close()
        self._frame_stream.close()
        self._event_thread.join(2.0)
        self._frame_thread.join(2.0)
        self._engine.shutdown()

    def _run_event_pump(self) -> None:
        while not self._stop_event.is_set():
            try:
                event = self._event_stream.read()
            except StreamClosedError:
                return
            self._dispatch_event(event)

    def _run_frame_pump(self) -> None:
        while not self._stop_event.is_set():
            try:
                first_frame = self._frame_stream.read()
            except StreamClosedError:
                return

            frames = [first_frame, *self._frame_stream.read_many()]
            latest_by_stream = {
                frame.stream_id: frame for frame in frames if isinstance(frame, FrameEnvelope)
            }
            self.bus._emit_frames(list(latest_by_stream.values()))

    def _dispatch_event(self, event: object) -> None:
        if isinstance(event, AcquisitionErrorEvent):
            self.acquisition._emit_error(event)
            return

        if isinstance(event, AcquisitionLifecycleEvent):
            self.acquisition._emit_lifecycle(event)
            return

        if isinstance(event, SettingChangedEvent):
            self.settings._emit_setting_changed(event)
            return

        if isinstance(event, DriverConnectionLostEvent):
            portal = self._driver_portals.get(event.driver_id)
            if portal is not None:
                portal._refresh_snapshot()
                portal._emit_connection_lost(event.detail)
            return

        if isinstance(event, BackendErrorEvent):
            self._dispatch_backend_error(event)
            return

        if isinstance(event, AcquisitionStateChangedEvent):
            self.acquisition._apply_snapshot(event.snapshot)

    def _dispatch_backend_error(self, event: BackendErrorEvent) -> None:
        if (
            event.source == "event_stream"
            and event.message == "EVENT_STREAM_OVERFLOW"
        ):
            self._resync_all()
            return

        if event.source == "stream_bus":
            self.bus._emit_error(event.message)
            return

        if event.source.startswith("driver_executor:"):
            driver_id = event.source.removeprefix("driver_executor:")
            portal = self._driver_portals.get(driver_id)
            if portal is not None:
                portal._emit_error(event.message)
            return

        if event.source == "frame_stream":
            self.bus._emit_error(event.message)

    def _resync_all(self) -> None:
        self.acquisition._apply_snapshot(self._engine.acquisition_snapshot())
        self.settings._resync_snapshot(self._engine.settings_snapshot())
        snapshots = {snapshot.driver_id: snapshot for snapshot in self._engine.driver_snapshots()}
        for driver_id, portal in self._driver_portals.items():
            snapshot = snapshots.get(driver_id)
            if snapshot is None:
                continue
            portal._apply_snapshot(snapshot)


def _flatten_settings(
    payload: dict[str, object],
    prefix: str = "",
) -> Iterable[tuple[str, object]]:
    for key, value in payload.items():
        qualified = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, dict):
            yield from _flatten_settings(value, qualified)
            continue
        yield qualified, value
