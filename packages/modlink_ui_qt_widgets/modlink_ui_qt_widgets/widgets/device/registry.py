from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtWidgets import QWidget

from modlink_qt_bridge import QtDriverPortal

from .panels import BaseDeviceControlPanel


class GenericDeviceControlPanel(BaseDeviceControlPanel):
    """Default device panel used for drivers without custom UI."""


_DEVICE_PANEL_REGISTRY: dict[str, type[BaseDeviceControlPanel]] = {}


def register_device_control_panel(
    driver_id: str,
) -> Callable[[type[BaseDeviceControlPanel]], type[BaseDeviceControlPanel]]:
    def _decorator(
        panel_cls: type[BaseDeviceControlPanel],
    ) -> type[BaseDeviceControlPanel]:
        _DEVICE_PANEL_REGISTRY[driver_id.strip()] = panel_cls
        return panel_cls

    return _decorator


def create_device_control_panel(
    portal: QtDriverPortal,
    parent: QWidget | None = None,
) -> BaseDeviceControlPanel:
    panel_cls = _DEVICE_PANEL_REGISTRY.get(portal.driver_id, GenericDeviceControlPanel)
    return panel_cls(portal, parent)
