from __future__ import annotations

from PyQt6.QtCore import QCoreApplication, QObject, pyqtSignal

from packages.modlink_drivers import DriverPortal

from ..acquisition import AcquisitionTask
from ..bus import StreamBus
from ..settings import SettingsService


class ModLinkRuntime(QObject):
    """Application runtime that owns shared services and driver threads."""

    sig_driver_event = pyqtSignal(object)
    sig_driver_started = pyqtSignal(str)
    sig_driver_stopped = pyqtSignal(str)
    sig_error = pyqtSignal(str)

    def __init__(
        self,
        *,
        settings: SettingsService | None = None,
        bus: StreamBus | None = None,
        acquisition: AcquisitionTask | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self.settings = settings or SettingsService(parent=self)
        self.bus = bus or StreamBus(parent=self)
        self.acquisition = acquisition or AcquisitionTask(self.bus, parent=self)
        self._driver_portals: dict[str, DriverPortal] = {}

        self.bus.sig_error.connect(self.sig_error.emit)

        app = QCoreApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self.shutdown)

    def attach_portal(
        self,
        portal: DriverPortal,
        *,
        auto_start: bool = False,
    ) -> DriverPortal:
        driver_id = portal.driver_id.strip()
        if not driver_id:
            raise ValueError("portal.driver_id must not be empty")
        if driver_id in self._driver_portals:
            raise ValueError(f"driver_id '{driver_id}' is already attached")
        if portal.parent() is None:
            portal.setParent(self)

        portal.sig_event.connect(self.sig_driver_event)
        portal.sig_started.connect(self.sig_driver_started)
        portal.sig_stopped.connect(self.sig_driver_stopped)
        portal.sig_error.connect(self.sig_error.emit)

        self._driver_portals[driver_id] = portal
        if auto_start:
            portal.start()
        return portal

    def driver_portal(self, driver_id: str) -> DriverPortal | None:
        return self._driver_portals.get(driver_id)

    def driver_portals(self) -> dict[str, DriverPortal]:
        return dict(self._driver_portals)

    def start_driver(self, driver_id: str) -> None:
        portal = self._require_portal(driver_id)
        portal.start()

    def stop_driver(self, driver_id: str, *, timeout_ms: int = 3000) -> None:
        portal = self._require_portal(driver_id)
        portal.stop(timeout_ms=timeout_ms)

    def start_all(self) -> None:
        for portal in self._driver_portals.values():
            portal.start()

    def stop_all(self, *, timeout_ms: int = 3000) -> None:
        for portal in self._driver_portals.values():
            portal.stop(timeout_ms=timeout_ms)

    def shutdown(self) -> None:
        self.stop_all()

    def _require_portal(self, driver_id: str) -> DriverPortal:
        portal = self.driver_portal(driver_id)
        if portal is None:
            raise KeyError(f"unknown driver_id '{driver_id}'")
        return portal
