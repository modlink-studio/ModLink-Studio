from __future__ import annotations

from collections.abc import Iterable

from modlink_core.settings.service import SettingsService

UI_LABELS_KEY = "ui.labels.items"
UI_PREVIEW_REFRESH_RATE_HZ_KEY = "ui.preview.refresh_rate_hz"
DEFAULT_LABELS = ("dry_swallow", "water_5ml", "cough")
PREVIEW_REFRESH_RATE_OPTIONS = (15, 24, 30, 60)
DEFAULT_PREVIEW_REFRESH_RATE_HZ = 30


def normalize_labels(values: object) -> tuple[str, ...]:
    if not isinstance(values, Iterable) or isinstance(values, (str, bytes)):
        return ()

    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value).strip()
        if not text or text in seen:
            continue
        normalized.append(text)
        seen.add(text)

    return tuple(normalized)


def load_labels(settings: SettingsService | None = None) -> tuple[str, ...]:
    service = settings or SettingsService.instance()
    labels = normalize_labels(service.get(UI_LABELS_KEY, list(DEFAULT_LABELS)))
    return labels or DEFAULT_LABELS


def save_labels(
    values: object,
    settings: SettingsService | None = None,
) -> tuple[str, ...]:
    service = settings or SettingsService.instance()
    labels = normalize_labels(values) or DEFAULT_LABELS
    service.set(UI_LABELS_KEY, list(labels))
    return labels


def normalize_preview_refresh_rate_hz(value: object) -> int:
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        return DEFAULT_PREVIEW_REFRESH_RATE_HZ

    if normalized in PREVIEW_REFRESH_RATE_OPTIONS:
        return normalized
    return DEFAULT_PREVIEW_REFRESH_RATE_HZ


def load_preview_refresh_rate_hz(
    settings: SettingsService | None = None,
) -> int:
    service = settings or SettingsService.instance()
    value = service.get(
        UI_PREVIEW_REFRESH_RATE_HZ_KEY,
        DEFAULT_PREVIEW_REFRESH_RATE_HZ,
    )
    return normalize_preview_refresh_rate_hz(value)


def save_preview_refresh_rate_hz(
    value: object,
    settings: SettingsService | None = None,
) -> int:
    service = settings or SettingsService.instance()
    refresh_rate_hz = normalize_preview_refresh_rate_hz(value)
    service.set(UI_PREVIEW_REFRESH_RATE_HZ_KEY, refresh_rate_hz)
    return refresh_rate_hz
