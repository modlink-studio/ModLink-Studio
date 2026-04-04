from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from modlink_sdk import DriverFactory

from ..acquisition import AcquisitionBackend
from ..bus import StreamBus
from ..drivers import DriverPortal
from ..event_stream import BackendEventBroker, EventStream
from ..events import (
    AcquisitionSnapshot,
    DriverSnapshot,
)
from ..settings import SettingsService

DEFAULT_DRIVER_STARTUP_TIMEOUT_MS = 5000


class ModLinkEngine:
    """Application engine that owns shared services and driver threads."""

    def __init__(
        self,
        driver_factories: Sequence[DriverFactory] = (),
        *,
        settings: SettingsService | None = None,
        parent: object | None = None,
    ) -> None:
        self._parent = parent
        self._event_broker = BackendEventBroker()
        self._settings = settings or SettingsService(parent=parent)
        self._settings.bind_event_publisher(self._event_broker.publish)
        self.bus = StreamBus(event_broker=self._event_broker, parent=self)
        self._acquisition = AcquisitionBackend(
            self.bus,
            settings=self._settings,
            publish_event=self._event_broker.publish,
            parent=self,
        )
        self._driver_portals: dict[str, DriverPortal] = {}
        attached_portals: list[DriverPortal] = []
        try:
            for factory in driver_factories:
                portal = self._attach_driver(factory)
                attached_portals.append(portal)
            self._acquisition.start()
        except Exception as exc:
            self._rollback_startup(attached_portals, exc)
            raise

    @property
    def settings(self) -> SettingsService:
        return self._settings

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
        return self._settings.snapshot()

    def open_event_stream(self, *, maxsize: int = 1024) -> EventStream:
        return self._event_broker.open_stream(maxsize=maxsize)

    def _attach_driver(self, driver_factory: DriverFactory) -> DriverPortal:
        portal = DriverPortal(
            driver_factory,
            publish_event=self._event_broker.publish,
            frame_sink=self.bus.ingest_frame,
            parent=self,
        )
        driver_id = portal.driver_id.strip()
        if driver_id in self._driver_portals:
            raise ValueError(f"driver_id '{driver_id}' is already installed")

        descriptors = portal.descriptors()
        self.bus.add_descriptors(descriptors)
        try:
            portal.start(timeout_ms=DEFAULT_DRIVER_STARTUP_TIMEOUT_MS)
        except Exception:
            for descriptor in descriptors:
                self.bus.remove_descriptor(descriptor.stream_id)
            raise

        self._driver_portals[driver_id] = portal
        return portal

    def _rollback_startup(
        self,
        attached_portals: list[DriverPortal],
        startup_error: Exception,
    ) -> None:
        cleanup_failures: list[str] = []
        for portal in reversed(attached_portals):
            try:
                portal.stop()
            except Exception as exc:
                cleanup_failures.append(
                    "cleanup failed while stopping driver "
                    f"'{portal.driver_id}': {type(exc).__name__}: {exc}"
                )
            for descriptor in portal.descriptors():
                self.bus.remove_descriptor(descriptor.stream_id)

        self._driver_portals.clear()
        try:
            self._acquisition.shutdown()
        except Exception as exc:
            cleanup_failures.append(
                f"cleanup failed while shutting down acquisition: {type(exc).__name__}: {exc}"
            )

        for note in cleanup_failures:
            startup_error.add_note(note)

    def shutdown(self) -> None:
        first_error: Exception | None = None
        for portal in self._driver_portals.values():
            try:
                portal.stop()
            except Exception as exc:
                if first_error is None:
                    first_error = exc
        self._driver_portals.clear()
        try:
            self._acquisition.shutdown()
        except Exception as exc:
            if first_error is None:
                first_error = exc
        if first_error is not None:
            raise first_error
