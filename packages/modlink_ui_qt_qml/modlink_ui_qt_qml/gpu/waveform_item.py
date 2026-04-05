from __future__ import annotations

from typing import Literal

import numpy as np
from PyQt6.QtCore import QRectF, Qt, pyqtProperty, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtQuick import QQuickPaintedItem


_COLORS = (
    "#2D8CF0",
    "#19BE6B",
    "#FF9F43",
    "#E74C3C",
    "#8E44AD",
    "#16A085",
    "#34495E",
    "#D35400",
)

_GRID_COLOR = QColor(180, 180, 180, 40)
_AXIS_LABEL_COLOR = QColor(120, 130, 140)
_CHANNEL_TITLE_COLOR = QColor(100, 110, 120)
_BG_COLOR = QColor(255, 255, 255)


class WaveformItem(QQuickPaintedItem):
    """GPU-backed QML item that renders multi-channel signal waveforms.

    Renders via QPainter into an FBO (QQuickPaintedItem.RenderTarget.FramebufferObject),
    composited by the QML Scene Graph on the GPU.
    """

    channelDataChanged = pyqtSignal()
    layoutModeChanged = pyqtSignal()
    windowSecondsChanged = pyqtSignal()
    sampleRateHzChanged = pyqtSignal()
    channelNamesChanged = pyqtSignal()
    channelColorsChanged = pyqtSignal()
    yRangeModeChanged = pyqtSignal()
    manualYMinChanged = pyqtSignal()
    manualYMaxChanged = pyqtSignal()

    def __init__(self, parent: QQuickPaintedItem | None = None) -> None:
        super().__init__(parent)
        self.setRenderTarget(QQuickPaintedItem.RenderTarget.FramebufferObject)
        self.setAntialiasing(True)

        self._channel_data: list[np.ndarray] = []
        self._layout_mode: Literal["stacked", "expanded"] = "expanded"
        self._window_seconds: float = 8.0
        self._sample_rate_hz: float = 250.0
        self._channel_names: list[str] = []
        self._channel_colors: list[str] = list(_COLORS)
        self._y_range_mode: str = "auto"
        self._manual_y_min: float = -1.0
        self._manual_y_max: float = 1.0

    # --- Properties ---

    @pyqtProperty("QVariantList", notify=channelDataChanged)
    def channelData(self) -> list[object]:
        return self._channel_data

    @channelData.setter  # type: ignore[attr-defined]
    def channelData(self, value: list[object]) -> None:
        arrays: list[np.ndarray] = []
        if isinstance(value, (list, tuple)):
            for item in value:
                arrays.append(np.asarray(item, dtype=np.float32).ravel())
        self._channel_data = arrays
        self.channelDataChanged.emit()
        self.update()

    @pyqtProperty(str, notify=layoutModeChanged)
    def layoutMode(self) -> str:
        return self._layout_mode

    @layoutMode.setter  # type: ignore[attr-defined]
    def layoutMode(self, value: str) -> None:
        if value in ("stacked", "expanded") and value != self._layout_mode:
            self._layout_mode = value  # type: ignore[assignment]
            self.layoutModeChanged.emit()
            self.update()

    @pyqtProperty(float, notify=windowSecondsChanged)
    def windowSeconds(self) -> float:
        return self._window_seconds

    @windowSeconds.setter  # type: ignore[attr-defined]
    def windowSeconds(self, value: float) -> None:
        if value != self._window_seconds and value > 0:
            self._window_seconds = value
            self.windowSecondsChanged.emit()
            self.update()

    @pyqtProperty(float, notify=sampleRateHzChanged)
    def sampleRateHz(self) -> float:
        return self._sample_rate_hz

    @sampleRateHz.setter  # type: ignore[attr-defined]
    def sampleRateHz(self, value: float) -> None:
        if value != self._sample_rate_hz and value > 0:
            self._sample_rate_hz = value
            self.sampleRateHzChanged.emit()
            self.update()

    @pyqtProperty("QVariantList", notify=channelNamesChanged)
    def channelNames(self) -> list[str]:
        return self._channel_names

    @channelNames.setter  # type: ignore[attr-defined]
    def channelNames(self, value: list[str]) -> None:
        self._channel_names = [str(v) for v in value] if value else []
        self.channelNamesChanged.emit()
        self.update()

    @pyqtProperty("QVariantList", notify=channelColorsChanged)
    def channelColors(self) -> list[str]:
        return self._channel_colors

    @channelColors.setter  # type: ignore[attr-defined]
    def channelColors(self, value: list[str]) -> None:
        self._channel_colors = [str(v) for v in value] if value else list(_COLORS)
        self.channelColorsChanged.emit()
        self.update()

    @pyqtProperty(str, notify=yRangeModeChanged)
    def yRangeMode(self) -> str:
        return self._y_range_mode

    @yRangeMode.setter  # type: ignore[attr-defined]
    def yRangeMode(self, value: str) -> None:
        if value != self._y_range_mode:
            self._y_range_mode = value
            self.yRangeModeChanged.emit()
            self.update()

    @pyqtProperty(float, notify=manualYMinChanged)
    def manualYMin(self) -> float:
        return self._manual_y_min

    @manualYMin.setter  # type: ignore[attr-defined]
    def manualYMin(self, value: float) -> None:
        if value != self._manual_y_min:
            self._manual_y_min = value
            self.manualYMinChanged.emit()
            self.update()

    @pyqtProperty(float, notify=manualYMaxChanged)
    def manualYMax(self) -> float:
        return self._manual_y_max

    @manualYMax.setter  # type: ignore[attr-defined]
    def manualYMax(self, value: float) -> None:
        if value != self._manual_y_max:
            self._manual_y_max = value
            self.manualYMaxChanged.emit()
            self.update()

    @pyqtSlot("QVariantList")
    def setChannelData(self, value: list[object]) -> None:
        self.channelData = value  # type: ignore[assignment]

    # --- Painting ---

    def paint(self, painter: QPainter) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        width = self.width()
        height = self.height()
        if width <= 0 or height <= 0 or not self._channel_data:
            painter.fillRect(QRectF(0, 0, width, height), _BG_COLOR)
            return

        if self._layout_mode == "stacked":
            self._paint_stacked(painter, width, height)
        else:
            self._paint_expanded(painter, width, height)

    def _paint_stacked(self, painter: QPainter, width: float, height: float) -> None:
        left_margin = 50.0
        right_margin = 10.0
        top_margin = 10.0
        bottom_margin = 30.0
        plot_rect = QRectF(left_margin, top_margin, width - left_margin - right_margin, height - top_margin - bottom_margin)

        painter.fillRect(QRectF(0, 0, width, height), _BG_COLOR)
        self._draw_grid(painter, plot_rect)
        self._draw_time_axis(painter, plot_rect, bottom_margin)

        y_min, y_max = self._resolve_y_range_stacked()
        self._draw_y_axis(painter, plot_rect, y_min, y_max)

        for channel_index, channel in enumerate(self._channel_data):
            color = self._color_for(channel_index)
            self._draw_waveform(painter, plot_rect, channel, y_min, y_max, color)

    def _paint_expanded(self, painter: QPainter, width: float, height: float) -> None:
        n = len(self._channel_data)
        if n == 0:
            painter.fillRect(QRectF(0, 0, width, height), _BG_COLOR)
            return

        left_margin = 50.0
        right_margin = 10.0
        top_margin = 4.0
        bottom_margin = 24.0
        gap = 4.0
        total_gap = gap * max(0, n - 1)
        available = height - top_margin - bottom_margin - total_gap
        subplot_height = max(20.0, available / n)

        painter.fillRect(QRectF(0, 0, width, height), _BG_COLOR)

        y_ranges = self._resolve_y_ranges_expanded()

        for channel_index, channel in enumerate(self._channel_data):
            top = top_margin + channel_index * (subplot_height + gap)
            plot_rect = QRectF(left_margin, top, width - left_margin - right_margin, subplot_height)

            self._draw_grid(painter, plot_rect)

            y_min, y_max = y_ranges[channel_index] if channel_index < len(y_ranges) else (0.0, 1.0)
            self._draw_y_axis(painter, plot_rect, y_min, y_max)

            name = self._channel_name(channel_index)
            painter.setPen(QPen(_CHANNEL_TITLE_COLOR))
            font = painter.font()
            font.setPixelSize(10)
            painter.setFont(font)
            painter.drawText(
                QRectF(plot_rect.left(), plot_rect.top() - 2, plot_rect.width(), 14),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom,
                name,
            )

            color = self._color_for(channel_index)
            self._draw_waveform(painter, plot_rect, channel, y_min, y_max, color)

            is_last = channel_index == n - 1
            if is_last:
                self._draw_time_axis(painter, plot_rect, bottom_margin)

    def _draw_waveform(
        self,
        painter: QPainter,
        rect: QRectF,
        data: np.ndarray,
        y_min: float,
        y_max: float,
        color: QColor,
    ) -> None:
        n = data.size
        if n < 2:
            return

        pen = QPen(color, 1.5)
        pen.setCosmetic(True)
        painter.setPen(pen)

        y_span = y_max - y_min
        if y_span <= 0:
            y_span = 1.0

        points_per_pixel = n / max(1.0, rect.width())
        if points_per_pixel > 4:
            stride = max(1, int(points_per_pixel / 2))
            indices = np.arange(0, n, stride)
            data = data[indices]
            n = data.size

        x_scale = rect.width() / max(1, n - 1)
        y_scale = rect.height() / y_span
        x_start = rect.left()
        y_bottom = rect.bottom()

        from PyQt6.QtCore import QPointF
        from PyQt6.QtGui import QPolygonF

        polygon = QPolygonF()
        polygon.resize(n)
        for i in range(n):
            x = x_start + i * x_scale
            y = y_bottom - (float(data[i]) - y_min) * y_scale
            polygon[i] = QPointF(x, y)

        painter.drawPolyline(polygon)

    def _draw_grid(self, painter: QPainter, rect: QRectF) -> None:
        painter.setPen(QPen(_GRID_COLOR, 1))
        for i in range(1, 4):
            y = rect.top() + rect.height() * i / 4
            painter.drawLine(QRectF(rect.left(), y, rect.width(), 0).topLeft(), QRectF(rect.right(), y, 0, 0).topLeft())
        for i in range(1, 5):
            x = rect.left() + rect.width() * i / 5
            painter.drawLine(QRectF(x, rect.top(), 0, rect.height()).topLeft(), QRectF(x, rect.bottom(), 0, 0).topLeft())

    def _draw_time_axis(self, painter: QPainter, rect: QRectF, bottom_margin: float) -> None:
        painter.setPen(QPen(_AXIS_LABEL_COLOR))
        font = painter.font()
        font.setPixelSize(10)
        painter.setFont(font)

        n = max(1, len(self._channel_data[0]) if self._channel_data else 1)
        t_start = -float(n - 1) / max(1.0, self._sample_rate_hz)
        t_end = 0.0

        label_rect = QRectF(rect.left(), rect.bottom() + 2, rect.width(), bottom_margin - 4)
        painter.drawText(label_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, f"{t_start:.1f}s")
        painter.drawText(label_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop, f"{t_end:.1f}s")
        painter.drawText(label_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, "Time (s)")

    def _draw_y_axis(self, painter: QPainter, rect: QRectF, y_min: float, y_max: float) -> None:
        painter.setPen(QPen(_AXIS_LABEL_COLOR))
        font = painter.font()
        font.setPixelSize(9)
        painter.setFont(font)

        label_width = 44.0
        label_rect_top = QRectF(rect.left() - label_width - 2, rect.top() - 6, label_width, 12)
        label_rect_bot = QRectF(rect.left() - label_width - 2, rect.bottom() - 6, label_width, 12)

        painter.drawText(label_rect_top, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, self._format_y(y_max))
        painter.drawText(label_rect_bot, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, self._format_y(y_min))

    def _resolve_y_range_stacked(self) -> tuple[float, float]:
        if self._y_range_mode == "manual":
            return self._manual_y_range()
        all_data = np.concatenate(self._channel_data) if self._channel_data else np.array([0.0])
        return self._auto_range(all_data)

    def _resolve_y_ranges_expanded(self) -> list[tuple[float, float]]:
        if self._y_range_mode == "manual":
            r = self._manual_y_range()
            return [r] * len(self._channel_data)
        return [self._auto_range(ch) for ch in self._channel_data]

    def _manual_y_range(self) -> tuple[float, float]:
        lo = min(self._manual_y_min, self._manual_y_max)
        hi = max(self._manual_y_min, self._manual_y_max)
        if hi <= lo:
            hi = lo + 1.0
        return (lo, hi)

    @staticmethod
    def _auto_range(data: np.ndarray) -> tuple[float, float]:
        if data.size == 0:
            return (0.0, 1.0)
        lo = float(np.nanmin(data))
        hi = float(np.nanmax(data))
        margin = max(abs(hi - lo) * 0.05, 1e-6)
        return (lo - margin, hi + margin)

    def _color_for(self, index: int) -> QColor:
        colors = self._channel_colors or list(_COLORS)
        return QColor(colors[index % len(colors)])

    def _channel_name(self, index: int) -> str:
        if index < len(self._channel_names) and self._channel_names[index]:
            return self._channel_names[index]
        return f"ch{index + 1}"

    @staticmethod
    def _format_y(value: float) -> str:
        if abs(value) >= 1000:
            return f"{value:.0f}"
        if abs(value) >= 1:
            return f"{value:.1f}"
        return f"{value:.3f}"
