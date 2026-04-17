from __future__ import annotations

import json
import keyword
from pathlib import Path
from typing import Any

from .item import SettingItem
from .spec import SettingsGroup, SettingsSpec, ValueSpec


def _validate_key(name: str, reserved: set[str] | frozenset[str]) -> None:
    if not isinstance(name, str):
        raise TypeError("setting key must be str")
    if name.startswith("_"):
        raise ValueError(f"invalid key: {name!r}")
    if not name.isidentifier() or keyword.iskeyword(name):
        raise ValueError(f"invalid key: {name!r}")
    if name in reserved:
        raise ValueError(f"reserved key: {name!r}")


class SettingsNode:
    RESERVED = frozenset({"add", "apply_dict", "dump_dict", "get_child", "path", "reset"})

    def __init__(self, *, name: str, parent: SettingsNode | None) -> None:
        object.__setattr__(self, "_name", name)
        object.__setattr__(self, "_parent", parent)
        object.__setattr__(self, "_children", {})

    @property
    def path(self) -> str:
        if self._parent is None:
            return ""
        base = self._parent.path
        return self._name if not base else f"{base}.{self._name}"

    def add(self, **specs: SettingsSpec) -> SettingsNode:
        for name, spec in specs.items():
            self._attach_spec(name, spec)
        return self

    def _attach_spec(self, name: str, spec: SettingsSpec) -> None:
        _validate_key(name, self.RESERVED)
        if not isinstance(spec, SettingsSpec):
            raise TypeError(f"{name!r} must be SettingsSpec")

        existing = self._children.get(name)
        if isinstance(spec, SettingsGroup):
            if existing is None:
                node = SettingsNode(name=name, parent=self)
                self._children[name] = node
            elif isinstance(existing, SettingsNode):
                node = existing
            else:
                raise KeyError(f"{self._full_path(name)} already exists as a setting")

            for child_name, child_spec in spec.children.items():
                node._attach_spec(child_name, child_spec)
            return

        if isinstance(spec, ValueSpec):
            if existing is not None:
                raise KeyError(f"duplicate key: {self._full_path(name)}")
            self._children[name] = SettingItem(name=name, parent=self, spec=spec)
            return

        raise TypeError(f"unsupported spec type: {type(spec).__name__}")

    def get_child(self, name: str) -> SettingsNode | SettingItem:
        child = self._children.get(name)
        if child is None:
            raise AttributeError(f"unknown key: {self._full_path(name)}")
        return child

    def __getattr__(self, name: str) -> SettingsNode | SettingItem:
        if name.startswith("_"):
            raise AttributeError(name)
        return self.get_child(name)

    def __setattr__(self, name: str, value: object) -> None:
        if name.startswith("_"):
            object.__setattr__(self, name, value)
            return

        child = self._children.get(name)
        full_path = self._full_path(name)
        if child is None:
            raise AttributeError(f"{full_path} is not declared; use .add(...)")
        if isinstance(child, SettingsNode):
            raise AttributeError(f"{full_path} is a group; cannot assign to a group")

        child.assign(value)

    def reset(self) -> None:
        for child in self._children.values():
            child.reset()

    def dump_dict(self) -> dict[str, object]:
        values: dict[str, object] = {}
        for name, child in self._children.items():
            if isinstance(child, SettingsNode):
                values[name] = child.dump_dict()
            else:
                values[name] = child.dump()
        return values

    def apply_dict(self, data: object) -> None:
        if not isinstance(data, dict):
            raise TypeError(f"{self.path or '<root>'} must be an object")

        for name, value in data.items():
            child = self._children.get(name)
            if child is None:
                raise KeyError(f"unknown key in file: {self._full_path(name)}")

            if isinstance(child, SettingsNode):
                if not isinstance(value, dict):
                    raise TypeError(f"{self._full_path(name)} must be an object")
                child.apply_dict(value)
                continue

            child.assign(value)

    def _full_path(self, name: str) -> str:
        return name if not self.path else f"{self.path}.{name}"


class SettingsStore:
    ROOT_RESERVED = frozenset({"add", "load", "path", "save", "snapshot"})

    def __init__(
        self,
        *,
        path: str | Path | None = None,
        version: int = 1,
        on_change: Any = None,
    ) -> None:
        object.__setattr__(self, "_path", None if path is None else Path(path))
        object.__setattr__(self, "_version", version)
        object.__setattr__(self, "_on_change", on_change)
        object.__setattr__(self, "_root", SettingsNode(name="", parent=None))

    @property
    def path(self) -> Path | None:
        return self._path

    def add(self, **specs: SettingsSpec) -> SettingsStore:
        overlap = self.ROOT_RESERVED.intersection(specs)
        if overlap:
            reserved_name = next(iter(sorted(overlap)))
            raise ValueError(f"reserved key: {reserved_name!r}")
        self._root.add(**specs)
        return self

    def __getattr__(self, name: str) -> SettingsNode | SettingItem:
        if name.startswith("_"):
            raise AttributeError(name)
        return self._root.get_child(name)

    def __setattr__(self, name: str, value: object) -> None:
        if name.startswith("_"):
            object.__setattr__(self, name, value)
            return
        setattr(self._root, name, value)

    def snapshot(self) -> dict[str, object]:
        return self._root.dump_dict()

    def save(self, path: str | Path | None = None) -> None:
        resolved_path = self._resolve_path(path)
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "_version": self._version,
            "values": self._root.dump_dict(),
        }
        temp_path = resolved_path.with_suffix(resolved_path.suffix + ".tmp")
        temp_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        temp_path.replace(resolved_path)

    def load(self, path: str | Path | None = None) -> None:
        resolved_path = self._resolve_path(path)
        payload = json.loads(resolved_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise TypeError("settings file must contain a JSON object")

        file_version = payload.get("_version")
        if file_version is not None and file_version != self._version:
            raise ValueError(
                f"settings version mismatch: file={file_version}, expected={self._version}"
            )

        values = payload.get("values", {})
        previous = self.snapshot()
        self._root.reset()
        try:
            self._root.apply_dict(values)
        except Exception:
            self._root.reset()
            self._root.apply_dict(previous)
            raise

    def _resolve_path(self, path: str | Path | None) -> Path:
        resolved_path = self._path if path is None else Path(path)
        if resolved_path is None:
            raise ValueError("path is required")
        return resolved_path


__all__ = ["SettingsNode", "SettingsStore"]
