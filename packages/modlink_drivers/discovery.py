from __future__ import annotations

from importlib.metadata import entry_points

from .base import DriverFactory

DRIVER_ENTRY_POINT_GROUP = "modlink.drivers"


def discover_driver_factories(
    *,
    group: str = DRIVER_ENTRY_POINT_GROUP,
) -> list[DriverFactory]:
    factories: list[DriverFactory] = []

    for entry_point in sorted(entry_points(group=group), key=lambda item: item.name):
        factory = entry_point.load()
        if not callable(factory):
            raise TypeError(
                f"entry point '{entry_point.name}' must resolve to a zero-argument factory, got {type(factory).__name__}"
            )
        factories.append(factory)

    return factories


__all__ = [
    "DRIVER_ENTRY_POINT_GROUP",
    "discover_driver_factories",
]
