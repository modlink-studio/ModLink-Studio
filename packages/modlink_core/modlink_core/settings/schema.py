from __future__ import annotations

import copy
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_MISSING = object()
_DELETE = object()


@dataclass(frozen=True)
class SettingsSpec:
    namespace: str
    schema: "GroupSettingSpec | Mapping[str, Any]"

    def __post_init__(self) -> None:
        if not self.namespace.strip():
            raise ValueError("settings namespace must not be empty")
        object.__setattr__(self, "schema", _coerce_group(self.schema))


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
    fields: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        normalized: dict[str, SettingNode] = {}
        for key, child in self.fields.items():
            if not isinstance(key, str) or not key.strip():
                raise ValueError("group setting keys must be non-empty strings")
            normalized[key] = _coerce_node(child)
        if not normalized:
            raise ValueError("group setting must contain at least one field")
        object.__setattr__(self, "fields", normalized)


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


def group(fields: Mapping[str, Any] | None = None, /, **entries: Any) -> GroupSettingSpec:
    payload: dict[str, Any] = {}
    if fields is not None:
        if not isinstance(fields, Mapping):
            raise TypeError("group fields must be a mapping")
        payload.update(fields)
    payload.update(entries)
    return GroupSettingSpec(fields=payload)


def bool_setting(*, default: bool = False, metadata: Mapping[str, Any] | None = None) -> BoolSettingSpec:
    return BoolSettingSpec(default=default, metadata=dict(metadata or {}))


def int_setting(
    *,
    default: int = 0,
    min_value: int | None = None,
    max_value: int | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> IntSettingSpec:
    return IntSettingSpec(
        default=default,
        min_value=min_value,
        max_value=max_value,
        metadata=dict(metadata or {}),
    )


def string_setting(
    *,
    default: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> StringSettingSpec:
    return StringSettingSpec(default=default, metadata=dict(metadata or {}))


def path_setting(
    *,
    default: Path | str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> PathSettingSpec:
    return PathSettingSpec(default=default, metadata=dict(metadata or {}))


def enum_setting(
    *,
    values: tuple[str, ...] | list[str],
    default: str,
    metadata: Mapping[str, Any] | None = None,
) -> EnumSettingSpec:
    return EnumSettingSpec(
        values=tuple(values),
        default=default,
        metadata=dict(metadata or {}),
    )


def _coerce_group(value: GroupSettingSpec | Mapping[str, Any]) -> GroupSettingSpec:
    if isinstance(value, GroupSettingSpec):
        return value
    if isinstance(value, Mapping):
        return GroupSettingSpec(fields=dict(value))
    raise TypeError("settings schema must be a GroupSettingSpec or mapping")


def _coerce_node(value: Any) -> SettingNode:
    if isinstance(value, SettingNode):
        return value
    if isinstance(value, Mapping):
        return GroupSettingSpec(fields=dict(value))
    raise TypeError("setting field must be a SettingNode or nested mapping")


__all__ = [
    "BoolSettingSpec",
    "EnumSettingSpec",
    "GroupSettingSpec",
    "IntSettingSpec",
    "PathSettingSpec",
    "SettingNode",
    "SettingsSpec",
    "StringSettingSpec",
    "ValueSettingSpec",
    "_DELETE",
    "_MISSING",
    "bool_setting",
    "enum_setting",
    "group",
    "int_setting",
    "path_setting",
    "string_setting",
]
