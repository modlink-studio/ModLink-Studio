from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from platformdirs import user_config_path

from modlink_sdk import DriverFactory

from ..bus import StreamBus
from ..core_settings import declare_core_settings
from ..drivers import DriverPortal, discover_driver_factories
from ..event_stream import BackendEventBroker, EventStream
from ..events import SettingChangedEvent
from ..models import DriverSnapshot, RecordingSnapshot
from ..recording import RecordingBackend
from ..settings import SettingsStore

DEFAULT_DRIVER_STARTUP_TIMEOUT_MS = 5000

logger = logging.getLogger(__name__)


class ModLinkEngine:
    """Application engine that owns shared services and driver threads."""

    def __init__(
        self,
        *,
        settings_path: str | Path | None = None,
        settings_version: int = 1,
        parent: object | None = None,
    ) -> None:
        resolved_driver_factories = tuple(discover_driver_factories())
        logger.info("Starting ModLink engine with %d driver factories", len(resolved_driver_factories))
        self._parent = parent
        self._event_broker = BackendEventBroker()
        self._settings = SettingsStore(
            path=_resolve_settings_path(settings_path),
            version=settings_version,
            on_change=self._publish_setting_changed,
        )
        declare_core_settings(self._settings)
        if self._settings.path is not None and self._settings.path.exists():
            self._settings.load(ignore_unknown=True)
        self.bus = StreamBus(event_broker=self._event_broker, parent=self)
        self._recording = RecordingBackend(
            self.bus,
            settings=self._settings,
            publish_event=self._event_broker.publish,
            parent=self,
        )
        self._driver_portals: dict[str, DriverPortal] = {}
        attached_portals: list[DriverPortal] = []
        try:
            for factory in resolved_driver_factories:
                portal = self._attach_driver(factory)
                attached_portals.append(portal)
            self._recording.start()
            logger.info("ModLink engine started with %d driver portals", len(self._driver_portals))
        except Exception as exc:
            logger.exception("Engine startup failed; rolling back attached services")
            self._rollback_startup(attached_portals, exc)
            raise

    @property
    def settings(self) -> SettingsStore:
        return self._settings

    @property
    def recording(self) -> RecordingBackend:
        return self._recording

    def recording_snapshot(self) -> RecordingSnapshot:
        return self._recording.snapshot()

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

    def _publish_setting_changed(self, key: str, value: Any) -> None:
        self._event_broker.publish(
            SettingChangedEvent(key=key, value=value, ts=time.time()),
        )

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
                logger.exception("Engine startup rollback failed while stopping driver '%s'", portal.driver_id)
                cleanup_failures.append(
                    "cleanup failed while stopping driver "
                    f"'{portal.driver_id}': {type(exc).__name__}: {exc}"
                )
            for descriptor in portal.descriptors():
                self.bus.remove_descriptor(descriptor.stream_id)

        self._driver_portals.clear()
        try:
            self._recording.shutdown()
        except Exception as exc:
            logger.exception("Engine startup rollback failed while shutting down recording")
            cleanup_failures.append(
                f"cleanup failed while shutting down recording: {type(exc).__name__}: {exc}"
            )

        for note in cleanup_failures:
            startup_error.add_note(note)

    def shutdown(self) -> None:
        logger.info("Shutting down ModLink engine")
        first_error: Exception | None = None
        for portal in self._driver_portals.values():
            try:
                portal.stop()
            except Exception as exc:
                logger.exception("Engine shutdown failed while stopping driver '%s'", portal.driver_id)
                if first_error is None:
                    first_error = exc
        self._driver_portals.clear()
        try:
            self._recording.shutdown()
        except Exception as exc:
            logger.exception("Engine shutdown failed while shutting down recording")
            if first_error is None:
                first_error = exc
        if first_error is not None:
            raise first_error
        logger.info("ModLink engine shut down")


def _resolve_settings_path(path: str | Path | None) -> Path:
    if path is not None:
        return Path(path)
    return Path(user_config_path("ModLink Studio", "ModLink")) / "settings.json"
