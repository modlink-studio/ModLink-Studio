from __future__ import annotations

import copy
import json
import logging
import os
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from threading import RLock
from typing import Any, Callable, Mapping

from platformdirs import user_data_path

logger = logging.getLogger(__name__)

_MISSING = object()
_DELETE = object()


def bool_setting(
    *,
    default: bool = False,
    scope: str | None = None,
    restart_required: bool = False,
) -> "BoolSettingSpec":
    return BoolSettingSpec(
        default=default,
        metadata={
            "scope": scope,
            "restart_required": restart_required,
        },
    )


def int_setting(
    *,
    default: int = 0,
    min_value: int | None = None,
    max_value: int | None = None,
    scope: str | None = None,
    restart_required: bool = False,
) -> "IntSettingSpec":
    return IntSettingSpec(
        default=default,
        min_value=min_value,
        max_value=max_value,
        metadata={
            "scope": scope,
            "restart_required": restart_required,
        },
    )


def str_setting(
    *,
    default: str | None = None,
    scope: str | None = None,
    restart_required: bool = False,
) -> "StringSettingSpec":
    return StringSettingSpec(
        default=default,
        metadata={
            "scope": scope,
            "restart_required": restart_required,
        },
    )


def path_setting(
    *,
    default: Path | str | None = None,
    scope: str | None = None,
    restart_required: bool = False,
) -> "PathSettingSpec":
    return PathSettingSpec(
        default=default,
        metadata={
            "scope": scope,
            "restart_required": restart_required,
        },
    )


def enum_setting(
    *,
    values: list[str] | tuple[str, ...],
    default: str,
    scope: str | None = None,
    restart_required: bool = False,
) -> "EnumSettingSpec":
    return EnumSettingSpec(
        values=tuple(values),
        default=default,
        metadata={
            "scope": scope,
            "restart_required": restart_required,
        },
    )


def group(**fields: "SettingNode") -> "GroupSettingSpec":
    return GroupSettingSpec(fields=fields)


@dataclass(frozen=True)
class SettingsSpec:
    namespace: str
    schema: "GroupSettingSpec"

    def __post_init__(self) -> None:
        if not self.namespace.strip():
            raise ValueError("settings namespace must not be empty")


class SettingNode:
    default: Any
    metadata: Mapping[str, Any]

    def deserialize(self, raw: Any, key: str) -> Any:
        del key
        return raw

    def serialize(self, value: Any, key: str) -> Any:
        del key
        return value


@dataclass(frozen=True)
class GroupSettingSpec(SettingNode):
    fields: dict[str, SettingNode] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "fields",
            dict(self.fields),
        )
        if not self.fields:
            raise ValueError("group setting must contain at least one field")


@dataclass(frozen=True)
class ValueSettingSpec(SettingNode):
    default: Any = _MISSING
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def deserialize(self, raw: Any, key: str) -> Any:
        del key
        return copy.deepcopy(raw)


@dataclass(frozen=True)
class BoolSettingSpec(ValueSettingSpec):
    default: bool = False

    def deserialize(self, raw: Any, key: str) -> bool:
        if not isinstance(raw, bool):
            raise ValueError(f"{key} must be a bool")
        return bool(raw)

    def serialize(self, value: Any, key: str) -> bool:
        if not isinstance(value, bool):
            raise ValueError(f"{key} must be a bool")
        return bool(value)


@dataclass(frozen=True)
class IntSettingSpec(ValueSettingSpec):
    default: int = 0
    min_value: int | None = None
    max_value: int | None = None

    def deserialize(self, raw: Any, key: str) -> int:
        if not isinstance(raw, int) or isinstance(raw, bool):
            raise ValueError(f"{key} must be an integer")
        if self.min_value is not None and raw < self.min_value:
            raise ValueError(f"{key} must be >= {self.min_value}")
        if self.max_value is not None and raw > self.max_value:
            raise ValueError(f"{key} must be <= {self.max_value}")
        return int(raw)

    def serialize(self, value: Any, key: str) -> int:
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f"{key} must be an integer")
        if self.min_value is not None and value < self.min_value:
            raise ValueError(f"{key} must be >= {self.min_value}")
        if self.max_value is not None and value > self.max_value:
            raise ValueError(f"{key} must be <= {self.max_value}")
        return int(value)


@dataclass(frozen=True)
class StringSettingSpec(ValueSettingSpec):
    default: str | None = None

    def deserialize(self, raw: Any, key: str) -> str | None:
        if raw is None:
            return None
        if not isinstance(raw, str):
            raise ValueError(f"{key} must be a string")
        return str(raw)

    def serialize(self, value: Any, key: str) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError(f"{key} must be a string")
        return value


@dataclass(frozen=True)
class PathSettingSpec(ValueSettingSpec):
    default: Path | str | None = None

    def deserialize(self, raw: Any, key: str) -> Path | None:
        del key
        if raw is None:
            return None
        text = str(raw).strip()
        if not text:
            return None
        return Path(text).expanduser()

    def serialize(self, value: Any, key: str) -> str | object:
        if value is None:
            return _DELETE
        if isinstance(value, Path):
            text = str(value)
        elif isinstance(value, str):
            text = value
        else:
            raise ValueError(f"{key} must be a path-like value")
        text = text.strip()
        if not text:
            raise ValueError(f"{key} must not be empty")
        return str(Path(text).expanduser())


@dataclass(frozen=True)
class EnumSettingSpec(ValueSettingSpec):
    values: tuple[str, ...] = field(default_factory=tuple)
    default: str = ""

    def __post_init__(self) -> None:
        values = tuple(self.values)
        if not values:
            raise ValueError("enum setting must define values")
        if self.default not in values:
            raise ValueError(f"default value {self.default!r} not in {values!r}")
        object.__setattr__(self, "values", values)

    def deserialize(self, raw: Any, key: str) -> str:
        if raw not in self.values:
            raise ValueError(f"{key} must be one of {self.values!r}")
        return str(raw)

    def serialize(self, value: Any, key: str) -> str:
        if str(value) not in self.values:
            raise ValueError(f"{key} must be one of {self.values!r}")
        return str(value)


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

    def bind(self, spec: SettingsSpec) -> "_SettingsBinding":
        if not isinstance(spec, SettingsSpec):
            raise TypeError("spec must be a SettingsSpec")
        return _SettingsBinding(
            store=self,
            prefix=(spec.namespace,),
            schema=spec.schema,
        )

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
            payload = self._payload
            current = payload
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


class _SettingsBinding:
    def __init__(
        self,
        *,
        store: SettingsStore,
        prefix: tuple[str, ...],
        schema: GroupSettingSpec,
    ) -> None:
        self._store = store
        self._prefix = prefix
        self._schema = schema

    @property
    def _full_prefix(self) -> str:
        return ".".join(self._prefix)

    def get(self, key: str, default: Any = None) -> Any:
        return self._store.get(f"{self._full_prefix}.{key}", default=default)

    def set(self, key: str, value: Any, *, persist: bool = True) -> None:
        if not isinstance(key, str) or not key:
            raise ValueError("setting key must not be empty")
        if key not in self._schema.fields:
            raise AttributeError(f"unknown setting key: {key}")
        child = self._schema.fields[key]
        if not isinstance(child, GroupSettingSpec):
            full_key = self._key(key)
            serialized = child.serialize(value, full_key)
            if serialized is _DELETE:
                self._store.remove(full_key, persist=persist)
                return
            self._store.set(full_key, serialized, persist=persist)
            return
        raise AttributeError(f"cannot set group key: {key}")

    def __getattr__(self, name: str) -> Any:
        child = self._schema.fields.get(name)
        if child is None:
            raise AttributeError(name)
        full_key = self._key(name)
        if isinstance(child, GroupSettingSpec):
            return _SettingsBinding(
                store=self._store,
                prefix=self._prefix + (name,),
                schema=child,
            )

        raw = self._store._get_raw(full_key)
        if raw is _MISSING:
            raw = child.default
            if raw is _MISSING:
                return None
        return child.deserialize(raw, full_key)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_"):
            object.__setattr__(self, name, value)
            return
        child = self._schema.fields.get(name)
        if child is None:
            raise AttributeError(f"unknown setting key: {name}")
        if isinstance(child, GroupSettingSpec):
            raise AttributeError(f"cannot assign to group key: {name}")

        full_key = self._key(name)
        serialized = child.serialize(value, full_key)
        if serialized is _DELETE:
            self._store.remove(full_key, persist=False)
            return
        self._store.set(full_key, serialized, persist=False)

    def _key(self, tail: str) -> str:
        return f"{self._full_prefix}.{tail}"


Settings = SettingsStore


__all__ = [
    "BoolSettingSpec",
    "EnumSettingSpec",
    "GroupSettingSpec",
    "IntSettingSpec",
    "PathSettingSpec",
    "Settings",
    "SettingsStore",
    "SettingsSpec",
    "StringSettingSpec",
    "bool_setting",
    "enum_setting",
    "group",
    "int_setting",
    "path_setting",
    "str_setting",
]
