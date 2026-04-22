from __future__ import annotations

from collections.abc import Iterable

from modlink_core.settings import SettingsGroup, SettingsList
from modlink_ui.bridge import QtSettingsBridge

UI_LABELS_KEY = "ui.labels.items"
DEFAULT_LABELS = ("default",)


def normalize_labels(values: object) -> tuple[str, ...]:
    if not isinstance(values, Iterable) or isinstance(values, (str, bytes)):
        return DEFAULT_LABELS

    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value).strip()
        if not text or text in seen:
            continue
        normalized.append(text)
        seen.add(text)

    return tuple(normalized) or DEFAULT_LABELS


def serialize_labels(values: tuple[str, ...]) -> list[str]:
    return list(values)


def declare_label_settings(settings: QtSettingsBridge) -> None:
    settings.add(
        ui=SettingsGroup(
            labels=SettingsGroup(
                items=SettingsList(default=list(DEFAULT_LABELS), item_cast=str),
            )
        )
    )
