from __future__ import annotations

from copy import deepcopy
from typing import Any, cast

from modlink_core.settings.service import SettingsService
from modlink_sdk import StreamDescriptor

from .models import (
    PreviewPayloadType,
    PreviewSettings,
    default_preview_settings,
    deserialize_preview_settings,
    normalize_preview_settings,
    serialize_preview_settings,
)

UI_PREVIEW_STREAMS_KEY = "ui.preview.streams"


class PreviewStreamSettingsStore:
    def __init__(self, settings: SettingsService | None = None) -> None:
        self._settings = settings or SettingsService.instance()

    def load(self, descriptor: StreamDescriptor) -> PreviewSettings:
        payload_type = self._payload_type(descriptor)
        streams = self._load_streams_map()
        entry = streams.get(descriptor.stream_id)
        if not isinstance(entry, dict):
            return default_preview_settings(payload_type)

        stored_payload_type = entry.get("payload_type")
        if stored_payload_type != payload_type:
            return default_preview_settings(payload_type)

        settings_payload = entry.get("settings")
        settings = deserialize_preview_settings(payload_type, settings_payload)
        return normalize_preview_settings(
            payload_type,
            settings,
            float(descriptor.nominal_sample_rate_hz or 1.0),
        )

    def save(self, descriptor: StreamDescriptor, preview_settings: PreviewSettings) -> None:
        payload_type = self._payload_type(descriptor)
        normalized = normalize_preview_settings(
            payload_type,
            preview_settings,
            float(descriptor.nominal_sample_rate_hz or 1.0),
        )

        streams = self._load_streams_map()
        streams[descriptor.stream_id] = {
            "payload_type": payload_type,
            "settings": serialize_preview_settings(normalized),
        }
        self._settings.set(UI_PREVIEW_STREAMS_KEY, streams, persist=True)

    def _load_streams_map(self) -> dict[str, dict[str, Any]]:
        raw = self._settings.get(UI_PREVIEW_STREAMS_KEY, {})
        if not isinstance(raw, dict):
            return {}
        return cast(dict[str, dict[str, Any]], deepcopy(raw))

    @staticmethod
    def _payload_type(descriptor: StreamDescriptor) -> PreviewPayloadType:
        payload_type = str(descriptor.payload_type)
        if payload_type not in {"signal", "raster", "field", "video"}:
            raise ValueError(f"unsupported payload_type: {payload_type}")
        return cast(PreviewPayloadType, payload_type)

