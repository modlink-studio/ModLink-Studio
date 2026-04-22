from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "AcquisitionActionState",
    "AcquisitionControlPanel",
    "AcquisitionFieldState",
    "AcquisitionFormValues",
    "AcquisitionPanelState",
    "AcquisitionViewModel",
]

_LAZY_IMPORTS = {
    "AcquisitionActionState": ".view_model",
    "AcquisitionControlPanel": ".panel",
    "AcquisitionFieldState": ".view_model",
    "AcquisitionFormValues": ".view_model",
    "AcquisitionPanelState": ".view_model",
    "AcquisitionViewModel": ".view_model",
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
