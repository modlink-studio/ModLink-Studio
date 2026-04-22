from __future__ import annotations

from threading import Event, Thread

from PyQt6.QtCore import QObject, Qt, pyqtSignal, pyqtSlot

from modlink_core.event_stream import (
    EventStream,
    EventStreamOverflowError,
    StreamClosedError,
)
from modlink_core.events import (
    DriverConnectionLostEvent,
    DriverExecutorFailedEvent,
    RecordingFailedEvent,
    SettingChangedEvent,
)
from modlink_core.runtime.engine import ModLinkEngine

from .bus import QtBusBridge
from .driver import QtDriverPortal
from .frame_pump import LatestFramePump
from .recording import QtRecordingBridge
from .replay import QtReplayBridge
from .settings import QtSettingsBridge


class QtModLinkBridge(QObject):
    _sig_event_received = pyqtSignal(object)
    _sig_resync_requested = pyqtSignal()

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
        self._is_shutdown = False
        self._stop_event = Event()
        self._event_stream: EventStream = engine.open_event_stream(maxsize=event_stream_maxsize)
        self.settings = QtSettingsBridge(engine.settings, parent=self)
        self.bus = QtBusBridge(engine.bus, parent=self)
        self._frame_pump = LatestFramePump(
            self.bus,
            thread_name="modlink.qt_bridge.frames",
        )
        self._frame_pump.attach_stream(
            engine.bus.open_frame_stream(
                maxsize=frame_stream_maxsize,
                drop_policy="drop_oldest",
                consumer_name="qt_bridge",
            )
        )
        self.recording = QtRecordingBridge(
            engine.recording,
            self.settings,
            parent=self,
        )
        self.replay = QtReplayBridge(
            engine.replay,
            self.settings,
            parent=self,
        )
        self._driver_portals = {
            portal.driver_id: QtDriverPortal(portal, parent=self)
            for portal in engine.driver_portals()
        }
        self._sig_event_received.connect(
            self._dispatch_event_on_qt_thread,
            Qt.ConnectionType.QueuedConnection,
        )
        self._sig_resync_requested.connect(
            self._resync_all_on_qt_thread,
            Qt.ConnectionType.QueuedConnection,
        )
        self._event_thread = Thread(
            target=self._run_event_pump,
            name="modlink.qt_bridge.events",
            daemon=True,
        )
        self._event_thread.start()

    def driver_portals(self) -> tuple[QtDriverPortal, ...]:
        return tuple(self._driver_portals.values())

    def driver_portal(self, driver_id: str) -> QtDriverPortal | None:
        return self._driver_portals.get(driver_id)

    def shutdown(self) -> None:
        if self._is_shutdown:
            return
        self._is_shutdown = True
        self._stop_event.set()
        self._event_stream.close()
        self._event_thread.join(2.0)
        self._frame_pump.shutdown()
        self.replay.shutdown()
        self._engine.shutdown()

    def _run_event_pump(self) -> None:
        while not self._stop_event.is_set():
            try:
                event = self._event_stream.read()
            except EventStreamOverflowError:
                self._sig_resync_requested.emit()
                continue
            except StreamClosedError:
                return
            self._sig_event_received.emit(event)

    @pyqtSlot(object)
    def _dispatch_event_on_qt_thread(self, event: object) -> None:
        if isinstance(event, RecordingFailedEvent):
            self.recording.handle_recording_failed(event)
            return

        if isinstance(event, SettingChangedEvent):
            self.settings.handle_setting_changed(event)
            return

        if isinstance(event, DriverConnectionLostEvent):
            portal = self._driver_portals.get(event.driver_id)
            if portal is not None:
                portal.handle_connection_lost(event.detail)
            return

        if isinstance(event, DriverExecutorFailedEvent):
            portal = self._driver_portals.get(event.driver_id)
            if portal is not None:
                portal.handle_executor_failed(event.detail)
            return

    @pyqtSlot()
    def _resync_all_on_qt_thread(self) -> None:
        self.recording.resync_from_backend()
        self.replay.resync_from_backend()
        self.settings.resync_from_backend()
        snapshots = {snapshot.driver_id: snapshot for snapshot in self._engine.driver_snapshots()}
        for driver_id, portal in self._driver_portals.items():
            snapshot = snapshots.get(driver_id)
            if snapshot is None:
                continue
            portal._apply_snapshot(snapshot)
