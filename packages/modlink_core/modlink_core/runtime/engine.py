from __future__ import annotations

from collections.abc import Sequence

from modlink_sdk import DriverFactory
from modlink_sdk.signals import Signal

from ..acquisition import AcquisitionBackend
from ..bus import StreamBus
from ..drivers import DriverPortal


class ModLinkEngine:
    """Application engine that owns shared services and driver threads."""

    def __init__(
        self,
        driver_factories: Sequence[DriverFactory] = (),
        parent: object | None = None,
    ) -> None:
        self.sig_error = Signal()
        self._parent = parent
        self.bus = StreamBus(parent=self)
        self._acquisition = AcquisitionBackend(self.bus, parent=self)
        self._driver_portals: dict[str, DriverPortal] = {}

        self.bus.sig_error.connect(self.sig_error.emit)
        self._acquisition.sig_error.connect(self.sig_error.emit)

        self._acquisition.start()

        for factory in driver_factories:
            self._attach_driver(factory)

    @property
    def acquisition(self) -> AcquisitionBackend:
        return self._acquisition

    def driver_portals(self) -> tuple[DriverPortal, ...]:
        return tuple(self._driver_portals.values())

    def driver_portal(self, driver_id: str) -> DriverPortal | None:
        return self._driver_portals.get(driver_id)

    def _attach_driver(self, driver_factory: DriverFactory) -> DriverPortal:
        portal = DriverPortal(driver_factory, parent=self)
        driver_id = portal.driver_id.strip()
        if driver_id in self._driver_portals:
            raise ValueError(f"driver_id '{driver_id}' is already installed")

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
