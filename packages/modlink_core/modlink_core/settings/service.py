from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from platformdirs import user_data_path

from ..events import BackendEventQueue, SettingChangedEvent


class SettingsService:
    """Global settings service shared across runtime modules."""

    _instance: SettingsService | None = None

    @classmethod
    def instance(cls) -> SettingsService:
        if cls._instance is None:
            return cls()
        return cls._instance

    def __init__(self, path: Path | None = None, parent: object | None = None) -> None:
        existing = type(self)._instance
        if existing is not None and existing is not self:
            raise RuntimeError(
                "SettingsService already exists; use SettingsService.instance()"
            )
        self._parent = parent
        self._path = path or self._resolve_path()
        self._settings = self._read_payload()
        self._event_queue: BackendEventQueue | None = None
        type(self)._instance = self

    def attach_event_queue(self, event_queue: BackendEventQueue) -> None:
        self._event_queue = event_queue

    def get(self, key: str, default: Any = None) -> Any:
        current = self._settings
        for part in self._parts(key):
            if not isinstance(current, dict) or part not in current:
                return default
            current = current[part]
        return current

    def set(self, key: str, value: Any, *, persist: bool = True) -> None:
        parts = self._parts(key)
        current = self._settings
        for part in parts[:-1]:
            nested = current.get(part)
            if not isinstance(nested, dict):
                nested = {}
                current[part] = nested
            current = nested
        current[parts[-1]] = value
        self._publish_setting_changed(key=key, value=value)
        if persist:
            self.save()

    def remove(self, key: str, *, persist: bool = True) -> None:
        parts = self._parts(key)
        current = self._settings
        for part in parts[:-1]:
            nested = current.get(part)
            if not isinstance(nested, dict):
                return
            current = nested
        if parts[-1] not in current:
            return
        current.pop(parts[-1], None)
        self._publish_setting_changed(key=key, value=None)
        if persist:
            self.save()

    def snapshot(self) -> dict[str, Any]:
        return json.loads(json.dumps(self._settings, ensure_ascii=False))

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(self._settings, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _publish_setting_changed(self, *, key: str, value: Any) -> None:
        if self._event_queue is None:
            return
        self._event_queue.publish(
            SettingChangedEvent(key=key, value=value, ts=time.time())
        )

    def _read_payload(self) -> dict[str, Any]:
        try:
            if self._path.exists():
                payload = json.loads(self._path.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    return payload
        except (OSError, json.JSONDecodeError):
            pass
        return {}

    def _resolve_path(self) -> Path:
        return user_data_path("ModLink Studio", appauthor=False) / "modlink_settings.json"

    def _parts(self, key: str) -> list[str]:
        normalized = [part.strip() for part in str(key).split(".") if part.strip()]
        if not normalized:
            raise ValueError("setting key must not be empty")
        return normalized
