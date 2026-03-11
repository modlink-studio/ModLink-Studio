from __future__ import annotations

from collections import deque

import numpy as np
from PyQt6.QtCore import QTimer, Qt, QRectF
from math import ceil, floor

from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, CaptionLabel

from ...backend import DeviceState, RecordEvent, StateEvent, StreamChunk


class SignalCanvas(QWidget):
    def __init__(
        self,
        max_samples: int = 2000,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self.max_samples = max_samples
        self._channel_names: tuple[str, ...] = ()
        self._last_sample_index: int | None = None
        self._x_buffer: deque[float] = deque(maxlen=max_samples)
        self._y_buffers: list[deque[float]] = []
        self._record_regions: list[tuple[int, int | None]] = []
        self._dirty = False

        self._colors = [
            QColor("#2979FF"),
            QColor("#FF6F00"),
            QColor("#2E7D32"),
            QColor("#C62828"),
            QColor("#6A1B9A"),
            QColor("#00838F"),
            QColor("#5D4037"),
            QColor("#455A64"),
        ]

        self.setMinimumHeight(280)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)

        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(33)
        self._refresh_timer.timeout.connect(self._flush_update)
        self._refresh_timer.start()

    @property
    def channel_names(self) -> tuple[str, ...]:
        return self._channel_names

    @property
    def has_samples(self) -> bool:
        return bool(self._x_buffer)

    def append_chunk(self, chunk: StreamChunk) -> None:
        if chunk.data.ndim != 2 or chunk.data.shape[1] != len(chunk.channel_names):
            return

        if self._channel_names != chunk.channel_names:
            self._channel_names = tuple(chunk.channel_names)
            self._y_buffers = [deque(maxlen=self.max_samples) for _ in self._channel_names]
            self.clear()

        n_samples = int(chunk.data.shape[0])
        if n_samples <= 0:
            return

        if self._last_sample_index is not None and chunk.sample_index0 <= self._last_sample_index:
            self.clear()

        x = np.arange(
            chunk.sample_index0,
            chunk.sample_index0 + n_samples,
            dtype=np.float64,
        )

        self._x_buffer.extend(x.tolist())
        for ch, y_buffer in enumerate(self._y_buffers):
            y_buffer.extend(chunk.data[:, ch].astype(np.float32).tolist())

        self._last_sample_index = int(x[-1])
        self._dirty = True

    def clear(self) -> None:
        self._x_buffer.clear()
        for buffer in self._y_buffers:
            buffer.clear()
        self._last_sample_index = None
        self._record_regions.clear()
        self._dirty = True
        self.update()

    def update_record_state(self, event: RecordEvent) -> None:
        anchor = event.sample_index
        if anchor is None:
            anchor = self._last_sample_index if self._last_sample_index is not None else 0

        if event.is_recording:
            if self._record_regions and self._record_regions[-1][1] is None:
                self._record_regions[-1] = (anchor, None)
            else:
                self._record_regions.append((anchor, None))
        else:
            if self._record_regions and self._record_regions[-1][1] is None:
                start_index = self._record_regions[-1][0]
                self._record_regions[-1] = (start_index, anchor)
            else:
                self._record_regions.append((anchor, anchor))

        self._dirty = True

    def _flush_update(self) -> None:
        if not self._dirty:
            return
        self._dirty = False
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.fillRect(self.rect(), QColor(255, 255, 255, 0))

        content_rect = self.rect().adjusted(12, 8, -12, -28)
        if content_rect.width() <= 1 or content_rect.height() <= 1:
            return

        painter.setPen(QPen(QColor(0, 0, 0, 20), 1))
        painter.setBrush(QColor(255, 255, 255, 120))
        painter.drawRoundedRect(QRectF(content_rect), 12, 12)

        clip_path = QPainterPath()
        clip_path.addRoundedRect(QRectF(content_rect.adjusted(1, 1, -1, -1)), 11, 11)

        if not self._channel_names:
            self._draw_placeholder(painter, content_rect, "等待通道信息")
            return

        if not self._x_buffer:
            painter.save()
            painter.setClipPath(clip_path)
            self._draw_grid(painter, content_rect, len(self._channel_names))
            painter.restore()
            self._draw_placeholder(painter, content_rect, "等待数据流")
            self._draw_footer(painter, "-", "-")
            return

        x = np.fromiter(self._x_buffer, dtype=np.float64)
        y_channels = [np.fromiter(buffer, dtype=np.float32) for buffer in self._y_buffers]
        n_channels = len(self._channel_names)

        visible_start = int(x[0])
        visible_end = int(x[-1])

        painter.save()
        painter.setClipPath(clip_path)
        self._draw_grid(painter, content_rect, n_channels)
        self._draw_record_regions(painter, content_rect, visible_start, visible_end)
        painter.restore()

        x_span = max(1.0, float(visible_end - visible_start))
        channel_height = content_rect.height() / max(1, n_channels)
        label_pen = QPen(QColor(55, 55, 55), 1)

        for index, (channel_name, y) in enumerate(zip(self._channel_names, y_channels)):
            top = content_rect.top() + index * channel_height
            channel_rect = QRectF(
                content_rect.left(),
                top,
                content_rect.width(),
                channel_height,
            )
            baseline = channel_rect.center().y()

            painter.setPen(label_pen)
            painter.drawText(
                QRectF(channel_rect.left() + 8, channel_rect.top() + 4, 80, 18),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                channel_name,
            )

            if y.size == 0:
                continue

            y_centered = y - float(np.mean(y))
            amplitude = float(np.max(np.abs(y_centered))) if y_centered.size else 0.0
            amplitude = max(amplitude, 1.0)
            y_scale = (channel_rect.height() * 0.34) / amplitude

            path = QPainterPath()
            for sample_idx, (sample_x, sample_y) in enumerate(zip(x, y_centered)):
                px = channel_rect.left() + ((float(sample_x) - visible_start) / x_span) * channel_rect.width()
                py = baseline - float(sample_y) * y_scale
                if sample_idx == 0:
                    path.moveTo(px, py)
                else:
                    path.lineTo(px, py)

            painter.setPen(QPen(self._colors[index % len(self._colors)], 1.4))
            painter.save()
            painter.setClipRect(channel_rect.adjusted(0, 0, 0, -1))
            painter.drawPath(path)
            painter.restore()

        self._draw_footer(painter, str(visible_start), str(visible_end))

    def _draw_grid(self, painter: QPainter, rect: QRectF, n_channels: int) -> None:
        painter.setPen(QPen(QColor(0, 0, 0, 14), 1))

        for step in range(1, 6):
            x = rect.left() + rect.width() * step / 6.0
            painter.drawLine(int(x), int(rect.top()), int(x), int(rect.bottom()))

        for index in range(n_channels + 1):
            y = rect.top() + rect.height() * index / max(1, n_channels)
            painter.drawLine(int(rect.left()), int(y), int(rect.right()), int(y))

    def _draw_placeholder(self, painter: QPainter, rect: QRectF, text: str) -> None:
        painter.setPen(QPen(QColor(105, 105, 105), 1))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

    def _draw_footer(self, painter: QPainter, start_text: str, end_text: str) -> None:
        footer_rect = self.rect().adjusted(14, self.height() - 22, -14, -6)
        painter.setPen(QPen(QColor(85, 85, 85), 1))
        painter.drawText(
            footer_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            f"sample index: {start_text}",
        )
        painter.drawText(
            footer_rect,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            end_text,
        )

    def _draw_record_regions(
        self,
        painter: QPainter,
        rect: QRectF,
        visible_start: int,
        visible_end: int,
    ) -> None:
        if visible_end <= visible_start:
            return

        fill_color = QColor(70, 201, 125, 36)
        line_pen = QPen(QColor(35, 160, 85), 2)

        for start_index, end_index in self._record_regions:
            region_end = visible_end if end_index is None else end_index
            if region_end < visible_start or start_index > visible_end:
                continue

            x0 = self._sample_to_x(rect, max(start_index, visible_start), visible_start, visible_end)
            x1 = self._sample_to_x(rect, min(region_end, visible_end), visible_start, visible_end)

            if end_index is None:
                x1 = rect.right()

            if x1 < x0:
                x0, x1 = x1, x0

            left = floor(x0)
            right = ceil(x1)
            painter.fillRect(
                QRectF(left, rect.top(), max(1.0, right - left), rect.height()),
                fill_color,
            )

            start_x = self._sample_to_x(rect, start_index, visible_start, visible_end)
            painter.setPen(line_pen)
            start_line_x = round(start_x)
            painter.drawLine(start_line_x, int(rect.top()), start_line_x, int(rect.bottom()))

            if end_index is not None:
                end_x = self._sample_to_x(rect, end_index, visible_start, visible_end)
                end_line_x = round(end_x)
                painter.drawLine(end_line_x, int(rect.top()), end_line_x, int(rect.bottom()))

    def _sample_to_x(
        self,
        rect: QRectF,
        sample_index: int,
        visible_start: int,
        visible_end: int,
    ) -> float:
        span = max(1.0, float(visible_end - visible_start))
        ratio = (float(sample_index) - float(visible_start)) / span
        ratio = min(1.0, max(0.0, ratio))
        return rect.left() + ratio * rect.width()


class StreamPlotWidget(QFrame):
    def __init__(
        self,
        max_samples: int = 2000,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self.max_samples = max_samples
        self._current_state: str = DeviceState.DISCONNECTED.value
        self._device_name: str = "-"
        self._last_seq: int | None = None
        self._last_fs: float | None = None

        self.setObjectName("stream-plot-widget")
        self.setStyleSheet(
            """
            QFrame#stream-plot-widget {
                background: rgba(255, 255, 255, 0.78);
                border: 1px solid rgba(0, 0, 0, 0.08);
                border-radius: 16px;
            }
            """
        )

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(20, 18, 20, 18)
        root_layout.setSpacing(12)

        self.title_label = BodyLabel("实时波形", self)
        self.status_label = CaptionLabel(
            "等待数据流。X 轴严格使用 sample_index0 对齐。",
            self,
        )
        self.status_label.setWordWrap(True)

        self.canvas = SignalCanvas(max_samples=max_samples, parent=self)

        root_layout.addWidget(self.title_label)
        root_layout.addWidget(self.status_label)
        root_layout.addWidget(self.canvas, 1)

    def set_state(self, event: StateEvent) -> None:
        self._current_state = event.state.value
        self._device_name = event.device_name or "-"
        self._update_status_text()
        if event.state in {
            DeviceState.DISCONNECTED,
            DeviceState.CONNECTING,
            DeviceState.DISCONNECTING,
            DeviceState.ERROR,
        }:
            self._last_seq = None
            self._last_fs = None
            self.canvas.clear()
            self._update_status_text()

    def update_stream(self, chunk: StreamChunk) -> None:
        self.canvas.append_chunk(chunk)
        self._last_seq = int(chunk.seq)
        self._last_fs = float(chunk.fs)
        self._update_status_text()

    def update_record_state(self, event: RecordEvent) -> None:
        self.canvas.update_record_state(event)

    def _update_status_text(self) -> None:
        if self.canvas.has_samples and self._last_seq is not None and self._last_fs is not None:
            self.status_label.setText(
                f"状态: {self._current_state} | 设备: {self._device_name} | "
                f"seq: {self._last_seq} | fs: {self._last_fs:.1f} Hz"
            )
            return

        self.status_label.setText(
            f"状态: {self._current_state} | 设备: {self._device_name} | "
            "等待数据流，X 轴严格使用 sample_index0"
        )
