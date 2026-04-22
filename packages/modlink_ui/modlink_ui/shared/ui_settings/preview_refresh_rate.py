from __future__ import annotations

from modlink_core.settings import SettingsGroup, SettingsInt
from modlink_ui.bridge import QtSettingsBridge

UI_PREVIEW_REFRESH_RATE_HZ_KEY = "ui.preview.refresh_rate_hz"
PREVIEW_REFRESH_RATE_OPTIONS = (15, 24, 30, 60)
DEFAULT_PREVIEW_REFRESH_RATE_HZ = 30


def normalize_preview_refresh_rate_hz(value: object) -> int:
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        return DEFAULT_PREVIEW_REFRESH_RATE_HZ

    if normalized in PREVIEW_REFRESH_RATE_OPTIONS:
        return normalized
    return DEFAULT_PREVIEW_REFRESH_RATE_HZ


def declare_preview_refresh_rate_settings(settings: QtSettingsBridge) -> None:
    settings.add(
        ui=SettingsGroup(
            preview=SettingsGroup(
                refresh_rate_hz=SettingsInt(default=DEFAULT_PREVIEW_REFRESH_RATE_HZ),
            )
        )
    )
