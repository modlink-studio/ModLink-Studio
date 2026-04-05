from __future__ import annotations

from typing import Literal

from PyQt6.QtCore import QRectF, Qt, pyqtProperty, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QColor, QImage, QPainter
from PyQt6.QtQuick import QQuickPaintedItem


_BG_COLOR = QColor(245, 247, 250)
_BORDER_COLOR = QColor(216, 228, 240)


class TextureItem(QQuickPaintedItem):
    """GPU-backed QML item that renders a QImage texture.

    Renders via QPainter into an FBO (QQuickPaintedItem.RenderTarget.FramebufferObject),
    composited by the QML Scene Graph on the GPU. Eliminates the need for
    base64 PNG encoding used in the previous Canvas-based approach.
    """

    sourceImageChanged = pyqtSignal()
    fillModeChanged = pyqtSignal()

    def __init__(self, parent: QQuickPaintedItem | None = None) -> None:
        super().__init__(parent)
        self.setRenderTarget(QQuickPaintedItem.RenderTarget.FramebufferObject)

        self._source_image: QImage | None = None
        self._fill_mode: Literal["fit", "fill", "stretch"] = "fit"

    @pyqtProperty(QImage, notify=sourceImageChanged)
    def sourceImage(self) -> QImage:
        image = self._source_image
        if image is None:
            return QImage()
        return image

    @pyqtProperty(str, notify=fillModeChanged)
    def fillMode(self) -> str:
        return self._fill_mode

    @fillMode.setter  # type: ignore[attr-defined]
    def fillMode(self, value: str) -> None:
        if value in ("fit", "fill", "stretch") and value != self._fill_mode:
            self._fill_mode = value  # type: ignore[assignment]
            self.fillModeChanged.emit()
            self.update()

    @sourceImage.setter  # type: ignore[attr-defined]
    def sourceImage(self, image: QImage | None) -> None:
        if image is None or image.isNull():
            self._source_image = None
        else:
            self._source_image = image
        self.sourceImageChanged.emit()
        self.update()

    @pyqtSlot(QImage)
    def setSourceImage(self, image: QImage) -> None:
        self.sourceImage = image

    def paint(self, painter: QPainter) -> None:
        width = self.width()
        height = self.height()
        if width <= 0 or height <= 0:
            return

        painter.fillRect(QRectF(0, 0, width, height), _BG_COLOR)

        image = self._source_image
        if image is None or image.isNull():
            painter.setPen(_BORDER_COLOR)
            painter.drawRect(QRectF(0.5, 0.5, width - 1, height - 1))
            return

        target_rect = self._compute_target_rect(image, width, height)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.drawImage(target_rect, image)

    def _compute_target_rect(self, image: QImage, width: float, height: float) -> QRectF:
        if self._fill_mode == "stretch":
            return QRectF(0, 0, width, height)

        iw = float(image.width())
        ih = float(image.height())
        if iw <= 0 or ih <= 0:
            return QRectF(0, 0, width, height)

        image_aspect = iw / ih
        view_aspect = width / height

        if self._fill_mode == "fit":
            if image_aspect > view_aspect:
                scaled_w = width
                scaled_h = width / image_aspect
            else:
                scaled_h = height
                scaled_w = height * image_aspect
        else:
            if image_aspect > view_aspect:
                scaled_h = height
                scaled_w = height * image_aspect
            else:
                scaled_w = width
                scaled_h = width / image_aspect

        x = (width - scaled_w) / 2.0
        y = (height - scaled_h) / 2.0
        return QRectF(x, y, scaled_w, scaled_h)
