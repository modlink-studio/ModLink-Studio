from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = ["DevicePage", "MainPage", "ReplayPage", "SettingsPage"]

_LAZY_IMPORTS = {
    "DevicePage": ".device",
    "MainPage": ".main",
    "ReplayPage": ".replay",
    "SettingsPage": ".settings",
}


def __getattr__(name: str) -> Any:
    module_name = _LAZY_IMPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module = import_module(module_name, __name__)
    value = getattr(module, name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
