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
        return self._spec.freeze(self._value)

    def assign(self, raw_value: object) -> None:
        self._value = self._spec.parse(raw_value)

    def dump(self) -> object:
        return self._spec.dump(self._value)
