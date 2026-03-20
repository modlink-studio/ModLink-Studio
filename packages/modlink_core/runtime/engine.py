from __future__ import annotations

from collections.abc import Sequence

from PyQt6.QtCore import QCoreApplication, QObject, pyqtSignal

from packages.modlink_drivers import DriverFactory, DriverPortal

from ..acquisition import AcquisitionBackend
from ..bus import StreamBus


class ModLinkEngine(QObject):
    """Application engine that owns shared services and driver threads."""

    sig_driver_event = pyqtSignal(object)
    sig_error = pyqtSignal(str)

    def __init__(
        self,
        driver_factories: Sequence[DriverFactory] = (),
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent=parent)

        self.bus = StreamBus(parent=self)
        self._acquisition = AcquisitionBackend(self.bus, parent=self)
        self._driver_portals: dict[str, DriverPortal] = {}

        self.bus.sig_error.connect(self.sig_error.emit)
        self._acquisition.sig_error.connect(self.sig_error.emit)

        self._acquisition.start()

        for factory in driver_factories:
            self._attach_driver(factory)

        app = QCoreApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self.shutdown)

    @property
    def acquisition(self) -> AcquisitionBackend:
        return self._acquisition

    def _attach_driver(self, driver_factory: DriverFactory) -> DriverPortal:
        portal = DriverPortal(driver_factory)
        driver_id = portal.driver_id.strip()
        if driver_id in self._driver_portals:
            raise ValueError(f"driver_id '{driver_id}' is already installed")

        portal.setParent(self)
        portal.sig_event.connect(self.sig_driver_event)
        portal.sig_error.connect(self.sig_error.emit)
        portal.sig_frame.connect(self.bus.ingest_frame)

        self.bus.add_descriptors(portal.descriptors())

        self._driver_portals[driver_id] = portal
        portal.start()
        return portal

    def shutdown(self) -> None:
        for portal in self._driver_portals.values():
            portal.stop()
        self._driver_portals.clear()
        self._acquisition.shutdown()
