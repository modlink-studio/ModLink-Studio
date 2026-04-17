from __future__ import annotations

from .spec import ValueSpec


class SettingItem:
    def __init__(self, *, name: str, parent: object, spec: ValueSpec) -> None:
        self._spec = spec
        self._value = spec.make_default()
        self._name = name
        self._parent = parent

    @property
    def path(self) -> str:
        base = self._parent.path
        return self._name if not base else f"{base}.{self._name}"

    @property
    def value(self) -> object:
        with self._parent._store._lock:
            return self._spec.snapshot(self._value)

    @property
    def spec(self) -> ValueSpec:
        return self._spec

    def assign(self, raw_value: object, *, notify: bool = True) -> bool:
        with self._parent._store._lock:
            previous = self._spec.snapshot(self._value)
            try:
                parsed = self._spec.parse(raw_value)
            except Exception as exc:
                message = f"{self.path}: {exc}"
                raise type(exc)(message) from exc
            changed = self._spec.snapshot(parsed) != previous
            self._value = parsed
            if changed and notify:
                self._parent._notify_value_changed(self)
            return changed

    def reset(self, *, notify: bool = False) -> bool:
        with self._parent._store._lock:
            previous = self._spec.snapshot(self._value)
            self._value = self._spec.make_default()
            changed = self._spec.snapshot(self._value) != previous
            if changed and notify:
                self._parent._notify_value_changed(self)
            return changed

    def dump(self) -> object:
        with self._parent._store._lock:
            return self._spec.dump(self._value)
