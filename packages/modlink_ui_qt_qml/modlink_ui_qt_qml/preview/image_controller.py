from __future__ import annotations

from dataclasses import replace

import numpy as np
from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QImage

from modlink_sdk import FrameEnvelope, StreamDescriptor

from .models import (
    FieldPreviewSettings,
    TransformMode,
    ValueRangeMode,
    normalize_preview_settings,
)

_COLORMAPS: dict[str, np.ndarray | None] = {"gray": None}


class ImageStreamController(QObject):
    """Controller for field-type (2D image) stream previews."""

    imageChanged = pyqtSignal(QImage)
    settingsChanged = pyqtSignal()

    def __init__(self, descriptor: StreamDescriptor, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._descriptor = descriptor
        self._settings = FieldPreviewSettings()
        self._latest_image: np.ndarray | None = None
        self._current_image = QImage()
        self._has_frame = False

    @property
    def descriptor(self) -> StreamDescriptor:
        return self._descriptor

    @property
    def payload_type(self) -> str:
        return "field"

    @property
    def has_frame(self) -> bool:
        return self._has_frame

    @pyqtProperty(str, notify=settingsChanged)
    def fillMode(self) -> str:
        return "fit"

    @pyqtProperty(QImage, notify=imageChanged)
    def currentImage(self) -> QImage:
        return self._current_image

    @pyqtProperty(str, notify=settingsChanged)
    def interpolation(self) -> str:
        return self._settings.interpolation

    @pyqtProperty(str, notify=settingsChanged)
    def transformMode(self) -> str:
        return self._settings.transform

    @pyqtProperty(str, notify=settingsChanged)
    def valueRangeMode(self) -> str:
        return self._settings.value_range_mode

    @pyqtProperty(float, notify=settingsChanged)
    def manualMin(self) -> float:
        return self._settings.manual_min

    @pyqtProperty(float, notify=settingsChanged)
    def manualMax(self) -> float:
        return self._settings.manual_max

    def apply_settings(self, settings: FieldPreviewSettings) -> None:
        self._settings = normalize_preview_settings(
            "field",
            settings,
            float(self._descriptor.nominal_sample_rate_hz or 1.0),
            tuple(self._descriptor.channel_names),
        )
        self.settingsChanged.emit()
        if self._has_frame:
            self.flush()

    def push_frame(self, frame: FrameEnvelope) -> None:
        data = np.asarray(frame.data)
        if data.ndim != 4 or data.shape[1] <= 0:
            return
        latest = np.asarray(data[:, -1, :, :])
        image = self._compose_image(latest)
        if image is None:
            return
        self._latest_image = image
        self._has_frame = True

    def flush(self) -> bool:
        if self._latest_image is None:
            return False
        image = self._apply_transform(self._latest_image, self._settings.transform)
        image = self._apply_levels(image, self._settings.value_range_mode, self._settings.manual_min, self._settings.manual_max)
        qimage = self._to_qimage(image)
        if qimage is not None:
            self._current_image = qimage
            self.imageChanged.emit(qimage)
            return True
        return False

    def export_settings(self) -> FieldPreviewSettings:
        return self._settings

    @pyqtSlot(str)
    def setInterpolation(self, value: str) -> None:
        if value not in ("nearest", "bilinear", "bicubic"):
            return
        self.apply_settings(replace(self._settings, interpolation=value))

    @pyqtSlot(str)
    def setTransformMode(self, value: str) -> None:
        if value not in (
            "none",
            "flip_horizontal",
            "flip_vertical",
            "rotate_90",
            "rotate_180",
            "rotate_270",
        ):
            return
        self.apply_settings(replace(self._settings, transform=value))

    @pyqtSlot(str)
    def setValueRangeMode(self, value: str) -> None:
        if value not in ("auto", "zero_to_one", "zero_to_255", "manual"):
            return
        self.apply_settings(replace(self._settings, value_range_mode=value))

    @pyqtSlot(float)
    def setManualMin(self, value: float) -> None:
        try:
            normalized = float(value)
        except (TypeError, ValueError):
            return
        self.apply_settings(replace(self._settings, manual_min=normalized))

    @pyqtSlot(float)
    def setManualMax(self, value: float) -> None:
        try:
            normalized = float(value)
        except (TypeError, ValueError):
            return
        self.apply_settings(replace(self._settings, manual_max=normalized))

    def _compose_image(self, latest: np.ndarray) -> np.ndarray | None:
        if latest.shape[0] == 1:
            return np.asarray(latest[0], dtype=np.float32)
        return np.asarray(np.mean(latest, axis=0), dtype=np.float32)

    @staticmethod
    def _apply_transform(image: np.ndarray, mode: TransformMode) -> np.ndarray:
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

    @staticmethod
    def _apply_levels(
        image: np.ndarray,
        mode: ValueRangeMode,
        manual_min: float,
        manual_max: float,
    ) -> np.ndarray:
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
        # auto
        flat = image.ravel()
        lo, hi = float(np.nanmin(flat)), float(np.nanmax(flat))
        if hi <= lo:
            return np.zeros(image.shape, dtype=np.uint8)
        scaled = (image - lo) / (hi - lo) * 255.0
        return np.clip(scaled, 0, 255).astype(np.uint8)

    @staticmethod
    def _to_qimage(image: np.ndarray) -> QImage | None:
        if image.ndim == 2:
            h, w = image.shape
            img = np.ascontiguousarray(image, dtype=np.uint8)
            return QImage(img.data, w, h, img.strides[0], QImage.Format.Format_Grayscale8).copy()
        if image.ndim == 3 and image.shape[2] == 3:
            h, w = image.shape[:2]
            img = np.ascontiguousarray(image, dtype=np.uint8)
            return QImage(img.data, w, h, img.strides[0], QImage.Format.Format_RGB888).copy()
        if image.ndim == 3 and image.shape[2] == 4:
            h, w = image.shape[:2]
            img = np.ascontiguousarray(image, dtype=np.uint8)
            return QImage(img.data, w, h, img.strides[0], QImage.Format.Format_RGBA8888).copy()
        return None
