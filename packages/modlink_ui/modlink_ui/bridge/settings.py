from __future__ import annotations

import time
from collections.abc import Iterable

from PyQt6.QtCore import QObject, pyqtSignal

from modlink_core.events import SettingChangedEvent
from modlink_core.settings import SettingsStore


class QtSettingsBridge(QObject):
    sig_setting_changed = pyqtSignal(object)

    def __init__(
        self,
        settings: SettingsStore,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self._settings = settings

    def add(self, **entries: object) -> object:
        return self._settings.add(**entries)

    def snapshot(self) -> dict[str, object]:
        return self._settings.snapshot()

    def load(self, *, ignore_unknown: bool = False) -> None:
        self._settings.load(ignore_unknown=ignore_unknown)

    def save(self) -> None:
        self._settings.save()

    def __getattr__(self, name: str) -> object:
        return getattr(self._settings, name)

    def handle_setting_changed(self, event: SettingChangedEvent) -> None:
        self.sig_setting_changed.emit(event)

    def resync_from_backend(self) -> None:
        self._resync_snapshot(self._settings.snapshot())

    def _resync_snapshot(self, snapshot: dict[str, object]) -> None:
        for key, value in _flatten_settings(snapshot):
            self.sig_setting_changed.emit(SettingChangedEvent(key=key, value=value, ts=time.time()))


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
