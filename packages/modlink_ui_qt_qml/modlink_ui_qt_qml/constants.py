from __future__ import annotations

from collections.abc import Iterable

from modlink_core.settings import settings_group, value_setting

UI_LABELS_KEY = "ui.labels.items"
DEFAULT_LABELS = ("default",)
UI_PREVIEW_REFRESH_RATE_HZ_KEY = "ui.preview.refresh_rate_hz"
PREVIEW_REFRESH_RATE_OPTIONS = (15, 24, 30, 60)
DEFAULT_PREVIEW_REFRESH_RATE_HZ = 30
UI_PREVIEW_STREAMS_KEY = "ui.preview.streams"


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


def normalize_preview_refresh_rate_hz(value: object) -> int:
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        return DEFAULT_PREVIEW_REFRESH_RATE_HZ
    if normalized in PREVIEW_REFRESH_RATE_OPTIONS:
        return normalized
    return DEFAULT_PREVIEW_REFRESH_RATE_HZ


def declare_label_settings(settings: object) -> None:
    settings.add(
        ui=settings_group(
            labels=settings_group(
                items=value_setting(default=DEFAULT_LABELS),
            )
        )
    )


def declare_preview_refresh_rate_settings(settings: object) -> None:
    settings.add(
        ui=settings_group(
            preview=settings_group(
                refresh_rate_hz=value_setting(default=DEFAULT_PREVIEW_REFRESH_RATE_HZ),
            )
        )
    )


def declare_preview_stream_settings(settings: object) -> None:
    settings.add(
        ui=settings_group(
            preview=settings_group(
                streams=value_setting(default={}),
            )
        )
    )
