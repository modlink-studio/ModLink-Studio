from __future__ import annotations

import numpy as np

from .image import ImageStreamView


class FieldStreamView(ImageStreamView):
    def _compose_image(self, latest: np.ndarray) -> np.ndarray:
        if latest.shape[0] == 1:
            return np.asarray(latest[0], dtype=np.float32)
        return np.asarray(np.mean(latest, axis=0), dtype=np.float32)
