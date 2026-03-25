from __future__ import annotations

from typing import Any

from ..models import VideoPreviewSettings


class VideoViewSettingsAdapter:
    def apply(self, view: Any, settings: VideoPreviewSettings) -> None:
        apply_preview_settings = getattr(view, "apply_preview_settings", None)
        if callable(apply_preview_settings):
            apply_preview_settings(settings)

