from __future__ import annotations

import copy
import json
import logging
import os
import tempfile
import time
from pathlib import Path
from threading import RLock
from typing import Any, Callable

from platformdirs import user_data_path

from .binding import _SettingsBinding
from .schema import SettingsSpec, _MISSING

logger = logging.getLogger(__name__)


class SettingsStore:
    """Persistent, thread-safe settings store."""

    def __init__(
        self,
        path: Path | str | None = None,
        *,
        on_change: Callable[[str, Any], None] | None = None,
    ) -> None:
        self._path = Path(path) if isinstance(path, str) else (path or self._resolve_path())
        self._lock = RLock()
        self._payload: dict[str, Any] = self._read_payload()
        self._on_change = on_change

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return copy.deepcopy(self._payload)

    def get(self, key: str, default: Any = None) -> Any:
        raw = self._get_raw(key)
        if raw is _MISSING:
            return copy.deepcopy(default)
        return copy.deepcopy(raw)

    def set(self, key: str, value: Any, *, persist: bool = True) -> None:
        self._set_raw(key, value, persist=persist)
        self._notify_if_changed(key, value)

    def remove(self, key: str, *, persist: bool = True) -> None:
        self._remove_raw(key, persist=persist)
        self._notify_if_changed(key, None)

    def save(self) -> None:
        with self._lock:
            self._save_locked()

    def bind(self, spec: SettingsSpec) -> _SettingsBinding:
        if not isinstance(spec, SettingsSpec):
            raise TypeError("spec must be a SettingsSpec")
        return _SettingsBinding.from_spec(self, spec)

    def _get_raw(self, key: str) -> Any:
        parts = self._parts(key)
        with self._lock:
            current: Any = self._payload
            for part in parts:
                if not isinstance(current, dict) or part not in current:
                    return _MISSING
                current = current[part]
            return current

    def _set_raw(self, key: str, value: Any, *, persist: bool) -> None:
        parts = self._parts(key)
        with self._lock:
            current = self._payload
            for part in parts[:-1]:
                child = current.get(part)
                if not isinstance(child, dict):
                    child = {}
                    current[part] = child
                current = child
            current[parts[-1]] = copy.deepcopy(value)
            if persist:
                self._save_locked()

    def _remove_raw(self, key: str, *, persist: bool) -> None:
        parts = self._parts(key)
        with self._lock:
            current: Any = self._payload
            parents: list[tuple[dict[str, Any], str]] = []
            for part in parts[:-1]:
                child = current.get(part)
                if not isinstance(child, dict):
                    return
                parents.append((current, part))
                current = child
            if parts[-1] not in current:
                return
            current.pop(parts[-1], None)
            while parents:
                parent, part = parents.pop()
                if current:
                    break
                parent.pop(part, None)
                current = parent
            if persist:
                self._save_locked()

    def _read_payload(self) -> dict[str, Any]:
        raw_payload: str | None = None
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
            if raw_payload is None:
                raise RuntimeError("failed to read settings payload") from exc
            backup_path = self._backup_corrupt_payload(raw_payload)
            logger.warning(
                "Settings file contained invalid JSON and was reset in memory: %s "
                "(backup: %s, error: %s)",
                self._path,
                backup_path,
                exc,
            )
            return {}
        except (OSError, UnicodeDecodeError) as exc:
            logger.warning(
                "Settings file could not be read and was reset in memory: %s (%s: %s)",
                self._path,
                type(exc).__name__,
                exc,
            )
            return {}
        return {}

    def _resolve_path(self) -> Path:
        return user_data_path("ModLink Studio", appauthor=False) / "modlink_settings.json"

    def _parts(self, key: str) -> list[str]:
        parts = [part.strip() for part in str(key).split(".") if part.strip()]
        if not parts:
            raise ValueError("setting key must not be empty")
        return parts

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

    def _notify_if_changed(self, key: str, value: Any) -> None:
        callback = self._on_change
        if callback is None:
            return
        try:
            callback(key, copy.deepcopy(value))
        except Exception:
            logger.exception("Settings change callback failed for key=%s", key)


__all__ = ["SettingsStore"]
