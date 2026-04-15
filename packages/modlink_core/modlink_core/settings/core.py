from __future__ import annotations

import copy
import json
import logging
import os
import tempfile
import time
from pathlib import Path
from threading import RLock

from platformdirs import user_data_path

logger = logging.getLogger(__name__)

_MISSING = object()
_DELETE = object()


class Settings:
    """Persistent settings stored in a single JSON file."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or self._resolve_path()
        self._lock = RLock()
        self._payload = self._read_payload()

    def save(self) -> None:
        with self._lock:
            self._save_locked()

    def _get_value(self, key: str) -> object:
        with self._lock:
            current: object = self._payload
            for part in self._parts(key):
                if not isinstance(current, dict) or part not in current:
                    return _MISSING
                current = current[part]
            return copy.deepcopy(current)

    def _set_value(self, key: str, value: object) -> None:
        parts = self._parts(key)
        with self._lock:
            current = self._payload
            for part in parts[:-1]:
                nested = current.get(part)
                if not isinstance(nested, dict):
                    nested = {}
                    current[part] = nested
                current = nested
            current[parts[-1]] = copy.deepcopy(value)

    def _remove_value(self, key: str) -> None:
        parts = self._parts(key)
        with self._lock:
            current = self._payload
            parents: list[tuple[dict[str, object], str]] = []
            for part in parts[:-1]:
                nested = current.get(part)
                if not isinstance(nested, dict):
                    return
                parents.append((current, part))
                current = nested
            if parts[-1] not in current:
                return
            current.pop(parts[-1], None)
            while parents and not current:
                parent, parent_key = parents.pop()
                parent.pop(parent_key, None)
                current = parent

    def _read_payload(self) -> dict[str, object]:
        with self._lock:
            try:
                if self._path.exists():
                    raw_payload = self._path.read_text(encoding="utf-8")
                    payload = json.loads(raw_payload)
                    if isinstance(payload, dict):
                        return payload
                    logger.warning(
                        "Settings file did not contain a JSON object; resetting in memory: %s",
                        self._path,
                    )
                    return {}
            except json.JSONDecodeError as exc:
                backup_path = self._backup_corrupt_payload(raw_payload)
                logger.warning(
                    "Settings file contained invalid JSON and was reset in memory: %s "
                    "(backup: %s, error: %s)",
                    self._path,
                    backup_path,
                    exc,
                )
            except (OSError, UnicodeDecodeError) as exc:
                logger.warning(
                    "Settings file could not be read and was reset in memory: %s (%s: %s)",
                    self._path,
                    type(exc).__name__,
                    exc,
                )
            return {}

    def _resolve_path(self) -> Path:
        return user_data_path("ModLink Studio", appauthor=False) / "modlink_settings.json"

    def _parts(self, key: str) -> list[str]:
        normalized = [part.strip() for part in str(key).split(".") if part.strip()]
        if not normalized:
            raise ValueError("setting key must not be empty")
        return normalized

    def _backup_corrupt_payload(self, raw_payload: str) -> Path | None:
        backup_path = self._path.with_name(f"{self._path.name}.corrupt-{time.time_ns()}.json")
        try:
            backup_path.write_text(raw_payload, encoding="utf-8")
        except OSError as exc:
            logger.warning(
                "Failed to write corrupt settings backup for %s to %s (%s: %s)",
                self._path,
                backup_path,
                type(exc).__name__,
                exc,
            )
            return None
        return backup_path

    def _save_locked(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(self._payload, ensure_ascii=False, indent=2)
        fd, temp_path = tempfile.mkstemp(
            prefix=f"{self._path.name}.",
            suffix=".tmp",
            dir=str(self._path.parent),
        )
        temp_file = Path(temp_path)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
            for attempt in range(5):
                try:
                    temp_file.replace(self._path)
                    break
                except PermissionError:
                    if attempt == 4:
                        raise
                    time.sleep(0.01 * (attempt + 1))
        finally:
            if temp_file.exists():
                temp_file.unlink(missing_ok=True)


class SettingField:
    def __init__(self, key: str, *, default: object = _MISSING) -> None:
        self.key = key
        self.default = default

    def __get__(self, obj: Settings | None, owner: type[Settings] | None = None) -> object:
        _ = owner
        if obj is None:
            return self
        raw_value = obj._get_value(self.key)
        if raw_value is _MISSING:
            return self._default_value()
        return self.load_value(raw_value)

    def __set__(self, obj: Settings, value: object) -> None:
        dumped = self.dump_value(value)
        if dumped is _DELETE:
            obj._remove_value(self.key)
            return
        obj._set_value(self.key, dumped)

    def load_value(self, value: object) -> object:
        return value

    def dump_value(self, value: object) -> object:
        return value

    def _default_value(self) -> object:
        if self.default is _MISSING:
            return None
        return copy.deepcopy(self.default)


class PathField(SettingField):
    def load_value(self, value: object) -> Path | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        return Path(text).expanduser()

    def dump_value(self, value: object) -> object:
        if value is None:
            return _DELETE
        text = str(value).strip()
        if not text:
            raise ValueError(f"{self.key} must not be empty")
        return str(Path(text).expanduser())


__all__ = ["PathField", "SettingField", "Settings"]
