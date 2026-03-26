from __future__ import annotations

import numpy as np

from .image import ImageStreamView


class VideoStreamView(ImageStreamView):
    def __init__(self, descriptor, parent=None) -> None:
        super().__init__(descriptor, parent=parent)
        self._color_format = "rgb"
        self._scale_mode = "fit"
        self._aspect_mode = "keep"

    def apply_preview_settings(self, settings: object) -> None:
        color_format = getattr(settings, "color_format", self._color_format)
        if isinstance(color_format, str):
            self._color_format = color_format

        scale_mode = getattr(settings, "scale_mode", self._scale_mode)
        if isinstance(scale_mode, str):
            self._scale_mode = scale_mode

        aspect_mode = getattr(settings, "aspect_mode", self._aspect_mode)
        if isinstance(aspect_mode, str):
            self._aspect_mode = aspect_mode

        super().apply_preview_settings(settings)
        self._apply_view_modes()

    def _render(self) -> None:
        super()._render()
        self._apply_view_modes()

    def _compose_image(self, latest: np.ndarray) -> np.ndarray:
        if self._color_format == "gray":
            return self._to_gray(latest)
        if self._color_format == "rgb":
            return self._to_rgb(latest, reverse=False)
        if self._color_format == "bgr":
            return self._to_rgb(latest, reverse=True)
        if self._color_format == "yuv":
            return self._yuv_to_rgb(latest)
        return self._to_gray(latest)

    def _to_rgb(self, latest: np.ndarray, *, reverse: bool) -> np.ndarray:
        if latest.shape[0] < 3:
            return self._to_gray(latest)
        channels = np.asarray(latest[:3], dtype=np.float32)
        if reverse:
            channels = channels[::-1]
        image = np.moveaxis(channels, 0, -1)
        return self._to_display_uint8(image)

    def _to_gray(self, latest: np.ndarray) -> np.ndarray:
        if latest.shape[0] == 1:
            return self._to_display_uint8(np.asarray(latest[0], dtype=np.float32))
        gray = np.mean(np.asarray(latest, dtype=np.float32), axis=0)
        return self._to_display_uint8(gray)

    def _yuv_to_rgb(self, latest: np.ndarray) -> np.ndarray:
        if latest.shape[0] < 3:
            return self._to_gray(latest)

        y = np.asarray(latest[0], dtype=np.float32)
        u = np.asarray(latest[1], dtype=np.float32)
        v = np.asarray(latest[2], dtype=np.float32)

        if np.max(np.abs(y)) > 1.5 or np.max(np.abs(u)) > 1.5 or np.max(np.abs(v)) > 1.5:
            y = y / 255.0
            u = u / 255.0 - 0.5
            v = v / 255.0 - 0.5

        r = y + 1.13983 * v
        g = y - 0.39465 * u - 0.58060 * v
        b = y + 2.03211 * u
        image = np.stack((r, g, b), axis=-1)
        return self._to_display_uint8(image)

    def _to_display_uint8(self, image: np.ndarray) -> np.ndarray:
        values = np.asarray(image, dtype=np.float32)
        max_value = float(np.max(values)) if values.size else 0.0
        min_value = float(np.min(values)) if values.size else 0.0
        if max_value <= 1.0 and min_value >= 0.0:
            values = values * 255.0
        values = np.clip(values, 0.0, 255.0)
        return values.astype(np.uint8, copy=False)

    def _apply_view_modes(self) -> None:
        keep_aspect = self._aspect_mode == "keep"
        self._view_box.setAspectLocked(keep_aspect)
        if self._latest_image is None:
            return

        image = np.asarray(self._latest_image)
        if image.ndim < 2:
            return
        height = float(image.shape[0])
        width = float(image.shape[1])
        if height <= 0.0 or width <= 0.0:
            return

        self._view_box.disableAutoRange()
        if self._scale_mode == "fit" or not keep_aspect:
            self._view_box.setRange(
                xRange=(0.0, width),
                yRange=(0.0, height),
                padding=0.0,
            )
            return

        view_rect = self._view_box.sceneBoundingRect()
        if view_rect.height() <= 0.0 or view_rect.width() <= 0.0:
            self._view_box.setRange(
                xRange=(0.0, width),
                yRange=(0.0, height),
                padding=0.0,
            )
            return

        view_aspect = float(view_rect.width() / view_rect.height())
        image_aspect = width / height
        if view_aspect > image_aspect:
            visible_height = width / view_aspect
            y0 = max(0.0, (height - visible_height) * 0.5)
            y1 = min(height, y0 + visible_height)
            self._view_box.setRange(
                xRange=(0.0, width),
                yRange=(y0, y1),
                padding=0.0,
            )
            return

        visible_width = height * view_aspect
        x0 = max(0.0, (width - visible_width) * 0.5)
        x1 = min(width, x0 + visible_width)
        self._view_box.setRange(
            xRange=(x0, x1),
            yRange=(0.0, height),
            padding=0.0,
        )
