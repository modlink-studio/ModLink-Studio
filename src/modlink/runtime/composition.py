from __future__ import annotations

from dataclasses import dataclass, field

from ..bus import StreamBus
from ..device import Device
from ..settings import SettingsService


@dataclass(slots=True)
class ModLinkRuntime:
    """Minimal application container for independent runtime modules."""

    settings: SettingsService = field(default_factory=SettingsService)
    bus: StreamBus = field(default_factory=StreamBus)
    devices: list[Device] = field(default_factory=list)

    def attach_device(self, device: Device) -> None:
        self.devices.append(device)
