from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OfficialPlugin:
    plugin_id: str
    distribution: str
    display_name: str
    description: str
    min_host_version: str
    max_host_version_exclusive: str


OFFICIAL_PLUGINS: tuple[OfficialPlugin, ...] = (
    OfficialPlugin(
        plugin_id="host-camera",
        distribution="modlink-plugin-host-camera",
        display_name="Host Camera",
        description="Camera capture driver for local webcam devices.",
        min_host_version="0.2.0",
        max_host_version_exclusive="0.3.0",
    ),
    OfficialPlugin(
        plugin_id="host-microphone",
        distribution="modlink-plugin-host-microphone",
        display_name="Host Microphone",
        description="Microphone capture driver for local audio input devices.",
        min_host_version="0.2.0",
        max_host_version_exclusive="0.3.0",
    ),
    OfficialPlugin(
        plugin_id="openbci-ganglion",
        distribution="modlink-plugin-openbci-ganglion",
        display_name="OpenBCI Ganglion",
        description="OpenBCI Ganglion driver over BLE or serial transport.",
        min_host_version="0.2.0",
        max_host_version_exclusive="0.3.0",
    ),
)


def get_official_plugin(plugin_id: str) -> OfficialPlugin:
    for plugin in OFFICIAL_PLUGINS:
        if plugin.plugin_id == plugin_id:
            return plugin
    raise KeyError(plugin_id)
