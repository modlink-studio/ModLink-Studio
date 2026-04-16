from __future__ import annotations

from copy import deepcopy
from types import MappingProxyType


class SettingsSpec:
    __slots__ = ()


class SettingsGroup(SettingsSpec):
    __slots__ = ("children",)

    def __init__(self, **children: SettingsSpec) -> None:
        self.children = dict(children)


class ValueSpec(SettingsSpec):
    __slots__ = ("default",)

    def __init__(self, default: object = None) -> None:
        self.default = default

    def make_default(self) -> object:
        return deepcopy(self.default)

    def parse(self, value: object) -> object:
        return value

    def freeze(self, value: object) -> object:
        return value

    def dump(self, value: object) -> object:
        return value


class SettingsInt(ValueSpec):
    __slots__ = ("min", "max")

    def __init__(
        self,
        default: int = 0,
        *,
        min: int | None = None,
        max: int | None = None,
    ) -> None:
        super().__init__(default)
        self.min = min
        self.max = max

    def parse(self, value: object) -> int:
        if isinstance(value, bool):
            raise TypeError("expected int")

        try:
            parsed = int(value)
        except (TypeError, ValueError) as exc:
            raise TypeError("expected int") from exc

        if self.min is not None and parsed < self.min:
            raise ValueError(f"value {parsed} < min {self.min}")
        if self.max is not None and parsed > self.max:
            raise ValueError(f"value {parsed} > max {self.max}")
        return parsed


class SettingsBool(ValueSpec):
    __slots__ = ()

    def __init__(self, default: bool = False) -> None:
        super().__init__(bool(default))

    def parse(self, value: object) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, int) and value in (0, 1):
            return bool(value)
        raise TypeError("expected bool")


class SettingsStr(ValueSpec):
    __slots__ = ()

    def __init__(self, default: str = "") -> None:
        super().__init__(str(default))

    def parse(self, value: object) -> str:
        if not isinstance(value, str):
            raise TypeError("expected str")
        return value


def _freeze_object(value: object) -> object:
    if isinstance(value, list):
        return tuple(_freeze_object(item) for item in value)
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze_object(item) for key, item in value.items()})
    if isinstance(value, set):
        return frozenset(_freeze_object(item) for item in value)
    return value


class SettingsList(ValueSpec):
    __slots__ = ("item_cast",)

    def __init__(self, default: list[object] | tuple[object, ...] | None = None, *, item_cast=None) -> None:
        super().__init__([] if default is None else list(default))
        self.item_cast = item_cast

    def parse(self, value: object) -> list[object]:
        if not isinstance(value, list):
            raise TypeError("expected list")
        if self.item_cast is None:
            parsed = list(value)
        else:
            parsed = [self.item_cast(item) for item in value]
        return deepcopy(parsed)

    def freeze(self, value: object) -> object:
        return _freeze_object(value)


__all__ = [
    "SettingsBool",
    "SettingsGroup",
    "SettingsInt",
    "SettingsList",
    "SettingsSpec",
    "SettingsStr",
    "ValueSpec",
]
