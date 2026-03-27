from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from modlink_sdk import DriverFactory

from ..events import (
    AcquisitionSnapshot,
    BackendEvent,
    BackendEventQueue,
    DriverSnapshot,
)
from ..acquisition import AcquisitionBackend
from ..bus import StreamBus
from ..drivers import DriverPortal
from ..settings import SettingsService


class ModLinkEngine:
    """Application engine that owns shared services and driver threads."""

    def __init__(
        self,
        driver_factories: Sequence[DriverFactory] = (),
        parent: object | None = None,
    ) -> None:
        self._parent = parent
        self._events = BackendEventQueue()
        self.bus = StreamBus(event_queue=self._events, parent=self)
        SettingsService.instance().attach_event_queue(self._events)
        self._acquisition = AcquisitionBackend(
            self.bus,
            event_queue=self._events,
            parent=self,
        )
        self._driver_portals: dict[str, DriverPortal] = {}

        self._acquisition.start()

        for factory in driver_factories:
            self._attach_driver(factory)

    @property
    def acquisition(self) -> AcquisitionBackend:
        return self._acquisition

    def acquisition_snapshot(self) -> AcquisitionSnapshot:
        return self._acquisition.snapshot()

    def driver_portals(self) -> tuple[DriverPortal, ...]:
        return tuple(self._driver_portals.values())

    def driver_snapshots(self) -> tuple[DriverSnapshot, ...]:
        return tuple(portal.snapshot() for portal in self._driver_portals.values())

    def driver_portal(self, driver_id: str) -> DriverPortal | None:
        return self._driver_portals.get(driver_id)

    def settings_snapshot(self) -> dict[str, Any]:
        return SettingsService.instance().snapshot()

    def drain_events(self, *, max_items: int | None = None) -> list[BackendEvent]:
        return self._events.drain(max_items=max_items)

    def _attach_driver(self, driver_factory: DriverFactory) -> DriverPortal:
        portal = DriverPortal(
            driver_factory,
            event_queue=self._events,
            frame_sink=self.bus.ingest_frame,
            parent=self,
        )
        driver_id = portal.driver_id.strip()
        if driver_id in self._driver_portals:
            raise ValueError(f"driver_id '{driver_id}' is already installed")

        self.bus.add_descriptors(portal.descriptors())

        self._driver_portals[driver_id] = portal
        portal.start()
        return portal

    def shutdown(self) -> None:
        for portal in self._driver_portals.values():
            portal.stop()
        self._driver_portals.clear()
        self._acquisition.shutdown()
