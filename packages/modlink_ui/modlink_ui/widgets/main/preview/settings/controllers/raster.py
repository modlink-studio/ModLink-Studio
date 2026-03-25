from __future__ import annotations

from typing import Any

from PyQt6.QtCore import QObject

from modlink_sdk import StreamDescriptor

from ..adapters.raster import RasterViewSettingsAdapter
from ..models import RasterPreviewSettings, normalize_preview_settings
from ..store import PreviewStreamSettingsStore


class RasterSettingsController(QObject):
    def __init__(
        self,
        descriptor: StreamDescriptor,
        section: Any,
        stream_view: Any,
        store: PreviewStreamSettingsStore,
        adapter: RasterViewSettingsAdapter,
    ) -> None:
        super().__init__()
        self._descriptor = descriptor
        self._section = section
        self._stream_view = stream_view
        self._store = store
        self._adapter = adapter
        self._updating = False
        self._section.sig_state_changed.connect(self._on_section_state_changed)

    def initialize(self) -> None:
        settings = self._load_and_normalize()
        self._set_section_state(settings)
        self._adapter.apply(self._stream_view, settings)

    def _on_section_state_changed(self, state: object) -> None:
        if self._updating:
            return
        if not isinstance(state, RasterPreviewSettings):
            return
        settings = self._normalize(state)
        self._store.save(self._descriptor, settings)
        self._adapter.apply(self._stream_view, settings)

    def _load_and_normalize(self) -> RasterPreviewSettings:
        loaded = self._store.load(self._descriptor)
        if not isinstance(loaded, RasterPreviewSettings):
            loaded = RasterPreviewSettings()
        return self._normalize(loaded)

    def _normalize(self, settings: RasterPreviewSettings) -> RasterPreviewSettings:
        normalized = normalize_preview_settings(
            "raster",
            settings,
            float(self._descriptor.nominal_sample_rate_hz or 1.0),
        )
        assert isinstance(normalized, RasterPreviewSettings)
        return normalized

    def _set_section_state(self, settings: RasterPreviewSettings) -> None:
        self._updating = True
        try:
            self._section.set_state(settings)
        finally:
            self._updating = False

