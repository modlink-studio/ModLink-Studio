from __future__ import annotations

from typing import Any

from ..models import RasterPreviewSettings


class RasterViewSettingsAdapter:
    def apply(self, view: Any, settings: RasterPreviewSettings) -> None:
        apply_preview_settings = getattr(view, "apply_preview_settings", None)
        if callable(apply_preview_settings):
            apply_preview_settings(settings)

