from __future__ import annotations

import numpy as np

from ..settings.models import FieldPreviewSettings
from .image import ImageStreamView


class FieldStreamView(ImageStreamView):
    def apply_preview_settings(self, settings: FieldPreviewSettings) -> None:
        if not isinstance(settings, FieldPreviewSettings):
            raise TypeError("field preview view requires FieldPreviewSettings")

        self._transform_mode = settings.transform
        self._colormap = settings.colormap
        self._value_range_mode = settings.value_range_mode
        self._manual_min = float(settings.manual_min)
        self._manual_max = float(settings.manual_max)
        self._interpolation = settings.interpolation
        self._apply_interpolation_mode()

        if self.has_frame:
            self._dirty = True

    def _compose_image(self, latest: np.ndarray) -> np.ndarray:
        if latest.shape[0] == 1:
            return np.asarray(latest[0], dtype=np.float32)
        return np.asarray(np.mean(latest, axis=0), dtype=np.float32)
