from __future__ import annotations

from copy import deepcopy
from numbers import Integral


class SettingsSpec:
    __slots__ = ()


class SettingsGroup(SettingsSpec):
    __slots__ = ("children",)

    def __init__(self, **children: SettingsSpec) -> None:
        for name, child in children.items():
            if not isinstance(child, SettingsSpec):
                raise TypeError(f"{name!r} must be SettingsSpec")
        self.children = dict(children)


class ValueSpec(SettingsSpec):
    __slots__ = ("default",)

    def __init__(self, default: object = None) -> None:
        self.default = default

    def make_default(self) -> object:
        return deepcopy(self.default)

    def parse(self, value: object) -> object:
        return value

    def snapshot(self, value: object) -> object:
        return value

    def dump(self, value: object) -> object:
        return deepcopy(value)


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

        if isinstance(value, Integral):
            parsed = value
        elif isinstance(value, str):
            text = value.strip()
            if not text:
                raise TypeError("expected int")
            digits = text[1:] if text[0] in "+-" else text
            if not digits.isdigit():
                raise TypeError("expected int")
            parsed = int(text)
        else:
            raise TypeError("expected int")

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


class SettingsList(ValueSpec):
    __slots__ = ("item_cast",)

    def __init__(
        self,
        default: list[object] | tuple[object, ...] | None = None,
        *,
        item_cast=None,
    ) -> None:
        super().__init__([] if default is None else list(default))
        self.item_cast = item_cast

    def parse(self, value: object) -> list[object]:
        if not isinstance(value, (list, tuple)):
            raise TypeError("expected list or tuple")

        items = list(value)
        if self.item_cast is None:
            parsed = items
        else:
            parsed = [self.item_cast(item) for item in items]
        return deepcopy(parsed)

    def snapshot(self, value: object) -> object:
        return tuple(deepcopy(value))
