from __future__ import annotations

from collections import deque

import numpy as np
from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal
from PyQt6.QtGui import QImage

from modlink_sdk import FrameEnvelope, StreamDescriptor

from .models import RasterPreviewSettings, TransformMode, ValueRangeMode

RASTER_WINDOW_SECONDS_OPTIONS = (1, 2, 4, 8, 12, 20)
DEFAULT_RASTER_WINDOW_SECONDS = 8


class RasterStreamController(QObject):
    imageChanged = pyqtSignal(QImage)
    settingsChanged = pyqtSignal()

    def __init__(self, descriptor: StreamDescriptor, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._descriptor = descriptor
        self._sample_rate_hz = max(1.0, float(descriptor.nominal_sample_rate_hz or 1.0))
        self._settings = RasterPreviewSettings()
        self._max_lines = self._compute_max_lines(self._settings.window_seconds)
        self._line_buffer: deque[np.ndarray] = deque(maxlen=self._max_lines)
        self._line_length = 0
        self._has_frame = False

    @property
    def descriptor(self) -> StreamDescriptor:
        return self._descriptor

    @property
    def payload_type(self) -> str:
        return "raster"

    @property
    def has_frame(self) -> bool:
        return self._has_frame

    @pyqtProperty(str, notify=settingsChanged)
    def fillMode(self) -> str:
        return "stretch"

    def apply_settings(self, settings: RasterPreviewSettings) -> None:
        old_ws = self._settings.window_seconds
        self._settings = settings
        if settings.window_seconds != old_ws:
            new_max = self._compute_max_lines(settings.window_seconds)
            if new_max != self._max_lines:
                self._max_lines = new_max
                self._line_buffer = deque(list(self._line_buffer)[-new_max:], maxlen=new_max)
        self.settingsChanged.emit()

    def push_frame(self, frame: FrameEnvelope) -> None:
        data = np.asarray(frame.data)
        if data.ndim != 3:
            return
        ch_count, time_count, line_length = data.shape
        if ch_count <= 0 or time_count <= 0 or line_length <= 0:
            return
        averaged = np.mean(np.asarray(data, dtype=np.float32), axis=0)
        for line in averaged:
            self._line_buffer.append(np.asarray(line, dtype=np.float32))
        self._line_length = int(line_length)
        self._has_frame = True

    def flush(self) -> bool:
        if not self._line_buffer or self._line_length <= 0:
            return False
        image = np.vstack(self._line_buffer)
        image = _apply_transform(image, self._settings.transform)
        image = _apply_levels(image, self._settings.value_range_mode, self._settings.manual_min, self._settings.manual_max)
        qimage = _to_qimage_gray(image)
        if qimage is not None:
            self.imageChanged.emit(qimage)
            return True
        return False

    def _compute_max_lines(self, window_seconds: int) -> int:
        return max(int(self._sample_rate_hz * window_seconds), 128)


class VideoStreamController(QObject):
    imageChanged = pyqtSignal(QImage)
    settingsChanged = pyqtSignal()

    def __init__(self, descriptor: StreamDescriptor, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._descriptor = descriptor
        from .models import VideoPreviewSettings
        self._settings = VideoPreviewSettings()
        self._latest_data: np.ndarray | None = None
        self._has_frame = False

    @property
    def descriptor(self) -> StreamDescriptor:
        return self._descriptor

    @property
    def payload_type(self) -> str:
        return "video"

    @property
    def has_frame(self) -> bool:
        return self._has_frame

    @pyqtProperty(str, notify=settingsChanged)
    def fillMode(self) -> str:
        mode = self._settings.aspect_mode
        if mode == "stretch":
            return "stretch"
        if self._settings.scale_mode == "fill":
            return "fill"
        return "fit"

    def apply_settings(self, settings: object) -> None:
        from .models import VideoPreviewSettings
        if isinstance(settings, VideoPreviewSettings):
            self._settings = settings
        self.settingsChanged.emit()

    def push_frame(self, frame: FrameEnvelope) -> None:
        data = np.asarray(frame.data)
        if data.ndim < 3:
            return
        if data.ndim == 4:
            data = data[:, -1, :, :]
        if data.ndim != 3:
            return
        self._latest_data = data
        self._has_frame = True

    def flush(self) -> bool:
        if self._latest_data is None:
            return False
        image = self._compose_image(self._latest_data)
        if image is None:
            return False
        image = _apply_transform(image, self._settings.transform)
        qimage = _ndarray_to_qimage(image)
        if qimage is not None:
            self.imageChanged.emit(qimage)
            return True
        return False

    def _compose_image(self, data: np.ndarray) -> np.ndarray | None:
        fmt = self._settings.color_format
        if fmt == "gray":
            return self._to_gray(data)
        if fmt == "rgb":
            return self._to_rgb(data, reverse=False)
        if fmt == "bgr":
            return self._to_rgb(data, reverse=True)
        if fmt == "yuv":
            return self._yuv_to_rgb(data)
        return self._to_gray(data)

    def _to_rgb(self, data: np.ndarray, *, reverse: bool) -> np.ndarray | None:
        if data.shape[0] < 3:
            return self._to_gray(data)
        channels = np.asarray(data[:3], dtype=np.float32)
        if reverse:
            channels = channels[::-1]
        image = np.moveaxis(channels, 0, -1)
        return _to_uint8(image)

    @staticmethod
    def _to_gray(data: np.ndarray) -> np.ndarray:
        if data.shape[0] == 1:
            return _to_uint8(np.asarray(data[0], dtype=np.float32))
        gray = np.mean(np.asarray(data, dtype=np.float32), axis=0)
        return _to_uint8(gray)

    @staticmethod
    def _yuv_to_rgb(data: np.ndarray) -> np.ndarray | None:
        if data.shape[0] < 3:
            gray = np.mean(np.asarray(data, dtype=np.float32), axis=0)
            return _to_uint8(gray)
        y = np.asarray(data[0], dtype=np.float32)
        u = np.asarray(data[1], dtype=np.float32)
        v = np.asarray(data[2], dtype=np.float32)
        if np.max(np.abs(y)) > 1.5 or np.max(np.abs(u)) > 1.5 or np.max(np.abs(v)) > 1.5:
            y, u, v = y / 255.0, u / 255.0 - 0.5, v / 255.0 - 0.5
        r = y + 1.13983 * v
        g = y - 0.39465 * u - 0.58060 * v
        b = y + 2.03211 * u
        image = np.stack((r, g, b), axis=-1)
        return _to_uint8(image)


def _to_uint8(image: np.ndarray) -> np.ndarray:
    values = np.asarray(image, dtype=np.float32)
    max_val = float(np.max(values)) if values.size else 0.0
    min_val = float(np.min(values)) if values.size else 0.0
    if max_val <= 1.0 and min_val >= 0.0:
        values = values * 255.0
    return np.clip(values, 0.0, 255.0).astype(np.uint8)


def _apply_transform(image: np.ndarray, mode: str) -> np.ndarray:
    if mode == "flip_horizontal":
        return np.fliplr(image)
    if mode == "flip_vertical":
        return np.flipud(image)
    if mode == "rotate_90":
        return np.rot90(image, k=1)
    if mode == "rotate_180":
        return np.rot90(image, k=2)
    if mode == "rotate_270":
        return np.rot90(image, k=3)
    return image


def _apply_levels(image: np.ndarray, mode: str, manual_min: float, manual_max: float) -> np.ndarray:
    if mode == "zero_to_one":
        return np.clip(image * 255.0, 0, 255).astype(np.uint8)
    if mode == "zero_to_255":
        return np.clip(image, 0, 255).astype(np.uint8)
    if mode == "manual":
        lo, hi = min(manual_min, manual_max), max(manual_min, manual_max)
        if hi <= lo:
            hi = lo + 1e-6
        scaled = (image - lo) / (hi - lo) * 255.0
        return np.clip(scaled, 0, 255).astype(np.uint8)
    flat = image.ravel()
    lo, hi = float(np.nanmin(flat)), float(np.nanmax(flat))
    if hi <= lo:
        return np.zeros(image.shape, dtype=np.uint8)
    scaled = (image - lo) / (hi - lo) * 255.0
    return np.clip(scaled, 0, 255).astype(np.uint8)


def _to_qimage_gray(image: np.ndarray) -> QImage | None:
    if image.ndim != 2:
        return None
    h, w = image.shape
    img = np.ascontiguousarray(image, dtype=np.uint8)
    return QImage(img.data, w, h, img.strides[0], QImage.Format.Format_Grayscale8).copy()


def _ndarray_to_qimage(image: np.ndarray) -> QImage | None:
    if image.ndim == 2:
        return _to_qimage_gray(image)
    if image.ndim == 3:
        h, w, c = image.shape
        img = np.ascontiguousarray(image, dtype=np.uint8)
        if c == 1:
            return QImage(img.data, w, h, img.strides[0], QImage.Format.Format_Grayscale8).copy()
        if c == 3:
            return QImage(img.data, w, h, img.strides[0], QImage.Format.Format_RGB888).copy()
        if c == 4:
            return QImage(img.data, w, h, img.strides[0], QImage.Format.Format_RGBA8888).copy()
    return None
