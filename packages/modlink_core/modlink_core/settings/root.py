from __future__ import annotations

import json
import keyword
from pathlib import Path
from threading import RLock
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


def _iter_slots(spec_type: type[object]) -> tuple[str, ...]:
    slots: list[str] = []
    seen: set[str] = set()
    for base in reversed(spec_type.__mro__):
        base_slots = getattr(base, "__slots__", ())
        if isinstance(base_slots, str):
            base_slots = (base_slots,)
        for name in base_slots:
            if name == "__weakref__" or name in seen:
                continue
            seen.add(name)
            slots.append(name)
    return tuple(slots)


def _specs_match(left: SettingsSpec, right: SettingsSpec) -> bool:
    if type(left) is not type(right):
        return False

    if isinstance(left, SettingsGroup):
        if left.children.keys() != right.children.keys():
            return False
        return all(_specs_match(left.children[name], right.children[name]) for name in left.children)

    if isinstance(left, ValueSpec):
        return all(
            getattr(left, name) == getattr(right, name)
            for name in _iter_slots(type(left))
        )

    return False


class SettingsNode:
    RESERVED = frozenset({"add", "apply_dict", "dump_dict", "get_child", "path", "reset"})

    def __init__(
        self,
        *,
        name: str,
        parent: SettingsNode | None,
        store: SettingsStore | None = None,
    ) -> None:
        object.__setattr__(self, "_name", name)
        object.__setattr__(self, "_parent", parent)
        object.__setattr__(self, "_store", store if store is not None else parent._store)
        object.__setattr__(self, "_children", {})

    @property
    def path(self) -> str:
        if self._parent is None:
            return ""
        base = self._parent.path
        return self._name if not base else f"{base}.{self._name}"

    def add(self, **specs: SettingsSpec) -> SettingsNode:
        with self._store._lock:
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
                if isinstance(existing, SettingItem) and _specs_match(existing.spec, spec):
                    return
                raise KeyError(f"duplicate key: {self._full_path(name)}")
            self._children[name] = SettingItem(name=name, parent=self, spec=spec)
            return

        raise TypeError(f"unsupported spec type: {type(spec).__name__}")

    def get_child(self, name: str) -> SettingsNode | SettingItem:
        with self._store._lock:
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

        with self._store._lock:
            child = self._children.get(name)
            full_path = self._full_path(name)
            if child is None:
                raise AttributeError(f"{full_path} is not declared; use .add(...)")
            if isinstance(child, SettingsNode):
                raise AttributeError(f"{full_path} is a group; cannot assign to a group")

            child.assign(value)

    def reset(self, *, notify: bool = False) -> None:
        with self._store._lock:
            for child in self._children.values():
                child.reset(notify=notify)

    def dump_dict(self) -> dict[str, object]:
        with self._store._lock:
            values: dict[str, object] = {}
            for name, child in self._children.items():
                if isinstance(child, SettingsNode):
                    values[name] = child.dump_dict()
                else:
                    values[name] = child.dump()
            return values

    def apply_dict(
        self,
        data: object,
        *,
        notify: bool = True,
        ignore_unknown: bool = False,
    ) -> None:
        with self._store._lock:
            if not isinstance(data, dict):
                raise TypeError(f"{self.path or '<root>'} must be an object")

            for name, value in data.items():
                child = self._children.get(name)
                if child is None:
                    if ignore_unknown:
                        continue
                    raise KeyError(f"unknown key in file: {self._full_path(name)}")

                if isinstance(child, SettingsNode):
                    if not isinstance(value, dict):
                        raise TypeError(f"{self._full_path(name)} must be an object")
                    child.apply_dict(value, notify=notify, ignore_unknown=ignore_unknown)
                    continue

                child.assign(value, notify=notify)

    def collect_leaf_values(self) -> dict[str, object]:
        with self._store._lock:
            values: dict[str, object] = {}
            for child in self._children.values():
                if isinstance(child, SettingsNode):
                    values.update(child.collect_leaf_values())
                    continue
                values[child.path] = child.value
            return values

    def _notify_value_changed(self, child: SettingItem) -> None:
        self._store._emit_change(child.path, child.value)

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
        object.__setattr__(self, "_lock", RLock())
        object.__setattr__(self, "_root", SettingsNode(name="", parent=None, store=self))

    @property
    def path(self) -> Path | None:
        return self._path

    def add(self, **specs: SettingsSpec) -> SettingsStore:
        with self._lock:
            overlap = self.ROOT_RESERVED.intersection(specs)
            if overlap:
                reserved_name = next(iter(sorted(overlap)))
                raise ValueError(f"reserved key: {reserved_name!r}")
            self._root.add(**specs)
        return self

    def __getattr__(self, name: str) -> SettingsNode | SettingItem:
        if name.startswith("_"):
            raise AttributeError(name)
        with self._lock:
            return self._root.get_child(name)

    def __setattr__(self, name: str, value: object) -> None:
        if name.startswith("_"):
            object.__setattr__(self, name, value)
            return
        with self._lock:
            setattr(self._root, name, value)

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            return self._root.dump_dict()

    def save(self, path: str | Path | None = None) -> None:
        with self._lock:
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

    def load(
        self,
        path: str | Path | None = None,
        *,
        ignore_unknown: bool = False,
    ) -> None:
        with self._lock:
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
            previous_snapshot = self.snapshot()
            previous = self._root.collect_leaf_values()
            self._root.reset(notify=False)
            try:
                self._root.apply_dict(values, notify=False, ignore_unknown=ignore_unknown)
            except Exception:
                self._root.reset(notify=False)
                self._root.apply_dict(previous_snapshot, notify=False)
                raise
            current = self._root.collect_leaf_values()
            for key, value in current.items():
                if previous.get(key) != value:
                    self._emit_change(key, value)

    def _resolve_path(self, path: str | Path | None) -> Path:
        resolved_path = self._path if path is None else Path(path)
        if resolved_path is None:
            raise ValueError("path is required")
        return resolved_path

    def _emit_change(self, key: str, value: object) -> None:
        on_change = self._on_change
        if on_change is None:
            return
        on_change(key, value)


__all__ = ["SettingsNode", "SettingsStore"]
