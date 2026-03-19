from __future__ import annotations

from PyQt6.QtCore import QCoreApplication, QObject, pyqtSignal

from packages.modlink_drivers import Driver, DriverPortal

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

    def install_driver(self, driver_type: type[Driver]) -> DriverPortal:
        if not isinstance(driver_type, type) or not issubclass(driver_type, Driver):
            raise TypeError("driver_type must be a Driver subclass")

        driver = driver_type()
        driver_id = driver.device_id.strip()
        if not driver_id:
            raise ValueError("driver.device_id must not be empty")
        if driver_id in self._driver_portals:
            raise ValueError(f"driver_id '{driver_id}' is already installed")

        portal = DriverPortal(driver, self.bus, parent=self)
        portal.sig_event.connect(self.sig_driver_event)
        portal.sig_started.connect(self.sig_driver_started)
        portal.sig_stopped.connect(self.sig_driver_stopped)
        portal.sig_error.connect(self.sig_error.emit)

        self._driver_portals[driver_id] = portal
        portal.start()
        return portal

    def shutdown(self) -> None:
        for portal in self._driver_portals.values():
            portal.stop()
