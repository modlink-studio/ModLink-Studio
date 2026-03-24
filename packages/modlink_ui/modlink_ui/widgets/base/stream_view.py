from __future__ import annotations

import numpy as np
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QVBoxLayout, QWidget

from modlink_core.settings.service import SettingsService
from modlink_sdk import FrameEnvelope, StreamDescriptor

import pyqtgraph as pg

UI_PREVIEW_REFRESH_RATE_HZ_KEY = "ui.preview.refresh_rate_hz"
DEFAULT_PREVIEW_REFRESH_RATE_HZ = 30


def normalize_preview_refresh_rate_hz(value: object) -> int:
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        return DEFAULT_PREVIEW_REFRESH_RATE_HZ

    if normalized in {15, 24, 30, 60}:
        return normalized
    return DEFAULT_PREVIEW_REFRESH_RATE_HZ


class BaseStreamView(QWidget):
    def __init__(
        self,
        descriptor: StreamDescriptor,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self.descriptor = descriptor
        self._settings = SettingsService.instance()
        self._dirty = False
        self._has_frame = False

        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._flush)
        self._apply_refresh_rate(self._load_refresh_rate_hz())
        self._settings.sig_setting_changed.connect(self._on_setting_changed)

    def push_frame(self, frame: FrameEnvelope) -> None:
        if not self._ingest_frame(frame):
            return
        self._has_frame = True
        self._dirty = True

    @property
    def has_frame(self) -> bool:
        return self._has_frame

    def _ingest_frame(self, frame: FrameEnvelope) -> bool:
        raise NotImplementedError

    def _render(self) -> None:
        raise NotImplementedError

    def _flush(self) -> None:
        if not self._dirty:
            return
        self._dirty = False
        self._render()

    def _on_setting_changed(self, event: object) -> None:
        if getattr(event, "key", None) != UI_PREVIEW_REFRESH_RATE_HZ_KEY:
            return
        self._apply_refresh_rate(self._load_refresh_rate_hz())

    def _load_refresh_rate_hz(self) -> int:
        return normalize_preview_refresh_rate_hz(
            self._settings.get(
                UI_PREVIEW_REFRESH_RATE_HZ_KEY,
                DEFAULT_PREVIEW_REFRESH_RATE_HZ,
            )
        )

    def _apply_refresh_rate(self, refresh_rate_hz: int) -> None:
        interval_ms = max(16, int(round(1000 / max(1, int(refresh_rate_hz)))))
        self._refresh_timer.start(interval_ms)


class ImageStreamView(BaseStreamView):
    def __init__(
        self,
        descriptor: StreamDescriptor,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(descriptor, parent=parent)
        self._latest_image: np.ndarray | None = None

        self._graphics_widget = pg.GraphicsLayoutWidget(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._graphics_widget, 1)

        self._last_shape: tuple[int, ...] | None = None
        self._graphics_widget.setBackground("transparent")
        self._view_box = self._graphics_widget.addViewBox()
        self._view_box.setAspectLocked(True)
        self._view_box.setMenuEnabled(False)
        self._view_box.setMouseEnabled(x=False, y=False)
        self._view_box.invertY(True)
        self._image_item = pg.ImageItem(axisOrder="row-major")
        self._view_box.addItem(self._image_item)

        self.setMinimumHeight(280)

    def _ingest_frame(self, frame: FrameEnvelope) -> bool:
        data = np.asarray(frame.data)
        image = self._extract_image(data)
        if image is None:
            return False
        self._latest_image = image
        return True

    def _render(self) -> None:
        if self._latest_image is None:
            return

        image = self._latest_image
        auto_range = image.shape != self._last_shape
        self._last_shape = image.shape
        self._image_item.setImage(image, autoLevels=True)
        if auto_range and self._view_box is not None:
            self._view_box.autoRange(padding=0.0)

    def _extract_image(self, data: np.ndarray) -> np.ndarray | None:
        if data.ndim != 4 or data.shape[1] <= 0:
            return None
        latest = np.asarray(data[:, -1, :, :])
        return self._normalize_image(self._compose_image(latest))

    def _compose_image(self, latest: np.ndarray) -> np.ndarray:
        raise NotImplementedError

    def _normalize_image(self, image: np.ndarray) -> np.ndarray:
        normalized = np.asarray(image)
        if normalized.ndim not in {2, 3}:
            return normalized
        if np.issubdtype(normalized.dtype, np.integer):
            return normalized

        minimum = float(np.min(normalized))
        maximum = float(np.max(normalized))
        if maximum <= minimum:
            return np.zeros_like(normalized, dtype=np.float32)
        return (normalized - minimum) / (maximum - minimum)
