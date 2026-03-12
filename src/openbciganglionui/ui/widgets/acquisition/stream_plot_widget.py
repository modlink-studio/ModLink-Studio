from __future__ import annotations

from collections import deque
from math import ceil, floor

import numpy as np
from PyQt6.QtCore import QLineF, QTimer, Qt, QRectF

from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen, QPixmap
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, CaptionLabel

from ....backend import (
    DeviceState,
    MarkerEvent,
    RecordEvent,
    SegmentEvent,
    StateEvent,
    StreamChunk,
)
from ...display_settings import DisplaySettings
from ...style_constants import DEFAULT_RADIUS, SMALL_RADIUS


class SignalCanvas(QWidget):
    def __init__(
        self,
        max_samples: int = 2000,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self.max_samples = max_samples
        self._channel_names: tuple[str, ...] = ()
        self._channel_visibility: tuple[bool, ...] = ()
        self._last_sample_index: int | None = None
        self._x_buffer: deque[float] = deque(maxlen=max_samples)
        self._y_buffers: list[deque[float]] = []
        self._markers: list[MarkerEvent] = []
        self._segments: list[tuple[int, int | None, str]] = []
        self._record_regions: list[tuple[int, int | None]] = []
        self._is_paused = False
        self._pause_snapshot: QPixmap | None = None
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

    def set_max_samples(self, max_samples: int) -> None:
        normalized = max(1, int(max_samples))
        if normalized == self.max_samples:
            return

        self.max_samples = normalized
        self._x_buffer = deque(list(self._x_buffer)[-normalized:], maxlen=normalized)
        self._y_buffers = [
            deque(list(buffer)[-normalized:], maxlen=normalized)
            for buffer in self._y_buffers
        ]
        self._last_sample_index = int(self._x_buffer[-1]) if self._x_buffer else None
        self._dirty = True
        self.update()

    def set_channel_visibility(self, channel_visibility: tuple[bool, ...]) -> None:
        visibility = tuple(bool(value) for value in channel_visibility)
        if visibility == self._channel_visibility:
            return

        self._channel_visibility = visibility
        self._dirty = True
        self.update()

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
        self._mark_dirty()

    def add_marker(self, event: MarkerEvent) -> None:
        self._markers.append(event)
        self._mark_dirty()

    def update_segment_state(self, event: SegmentEvent) -> None:
        if event.action == "started":
            self._segments.append((event.start_sample_index, None, event.label))
            self._mark_dirty()
            return

        if event.action == "stopped":
            for index in range(len(self._segments) - 1, -1, -1):
                start_sample_index, end_sample_index, label = self._segments[index]
                if end_sample_index is None and start_sample_index == event.start_sample_index:
                    self._segments[index] = (
                        start_sample_index,
                        event.end_sample_index,
                        label,
                    )
                    break
            self._mark_dirty()

    def clear(self) -> None:
        self._x_buffer.clear()
        for buffer in self._y_buffers:
            buffer.clear()
        self._last_sample_index = None
        self._markers.clear()
        self._segments.clear()
        self._record_regions.clear()
        self._pause_snapshot = None
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

        self._mark_dirty()

    def set_paused(self, is_paused: bool) -> None:
        if self._is_paused == is_paused:
            return

        if is_paused:
            self._flush_update()
            self._pause_snapshot = self.grab()
            self._is_paused = True
            return

        self._is_paused = False
        self._pause_snapshot = None
        self._dirty = False
        self.update()

    def _flush_update(self) -> None:
        if self._is_paused:
            return
        if not self._dirty:
            return
        self._dirty = False
        self.update()

    def _mark_dirty(self) -> None:
        self._dirty = True
        if not self._is_paused:
            self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.fillRect(self.rect(), QColor(255, 255, 255, 0))

        if self._is_paused and self._pause_snapshot is not None:
            painter.drawPixmap(self.rect(), self._pause_snapshot)
            return

        content_rect = self.rect().adjusted(12, 8, -12, -28)
        if content_rect.width() <= 1 or content_rect.height() <= 1:
            return

        frame_pen = QPen(QColor(0, 0, 0, 20), 1.0)
        frame_pen.setCosmetic(True)
        painter.setPen(frame_pen)
        painter.setBrush(QColor(255, 255, 255, 120))
        painter.drawRoundedRect(QRectF(content_rect), DEFAULT_RADIUS, DEFAULT_RADIUS)

        clip_path = QPainterPath()
        clip_path.addRoundedRect(
            QRectF(content_rect.adjusted(1, 1, -1, -1)),
            SMALL_RADIUS,
            SMALL_RADIUS,
        )

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
        visible_indices = [
            index
            for index, _channel_name in enumerate(self._channel_names)
            if self._is_channel_visible(index)
        ]

        visible_start = int(x[0])
        visible_end = int(x[-1])

        painter.save()
        painter.setClipPath(clip_path)
        self._draw_grid(painter, content_rect, max(1, len(visible_indices)))
        self._draw_record_regions(painter, content_rect, visible_start, visible_end)
        self._draw_segment_regions(painter, content_rect, visible_start, visible_end)
        painter.restore()

        if not visible_indices:
            self._draw_placeholder(painter, content_rect, "当前未启用任何通道")
            self._draw_footer(painter, str(visible_start), str(visible_end))
            return

        x_span = max(1.0, float(visible_end - visible_start))
        channel_height = content_rect.height() / len(visible_indices)
        label_pen = QPen(QColor(55, 55, 55), 1.0)
        label_pen.setCosmetic(True)

        for visible_row, channel_index in enumerate(visible_indices):
            channel_name = self._channel_names[channel_index]
            y = y_channels[channel_index]
            top = content_rect.top() + visible_row * channel_height
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

            signal_pen = QPen(self._colors[channel_index % len(self._colors)], 1.35)
            signal_pen.setCosmetic(True)
            signal_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            signal_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.save()
            painter.setPen(signal_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setClipRect(channel_rect.adjusted(0, 0, 0, -1))
            painter.drawPath(path)
            painter.restore()

        painter.save()
        painter.setClipPath(clip_path)
        self._draw_markers(painter, content_rect, visible_start, visible_end)
        painter.restore()

        self._draw_footer(painter, str(visible_start), str(visible_end))

    def _draw_grid(self, painter: QPainter, rect: QRectF, n_channels: int) -> None:
        grid_pen = QPen(QColor(0, 0, 0, 14), 1.0)
        grid_pen.setCosmetic(True)
        painter.setPen(grid_pen)

        for step in range(1, 6):
            x = rect.left() + rect.width() * step / 6.0
            painter.drawLine(QLineF(x, rect.top(), x, rect.bottom()))

        for index in range(n_channels + 1):
            y = rect.top() + rect.height() * index / max(1, n_channels)
            painter.drawLine(QLineF(rect.left(), y, rect.right(), y))

    def _draw_placeholder(self, painter: QPainter, rect: QRectF, text: str) -> None:
        placeholder_pen = QPen(QColor(105, 105, 105), 1.0)
        placeholder_pen.setCosmetic(True)
        painter.setPen(placeholder_pen)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

    def _draw_footer(self, painter: QPainter, start_text: str, end_text: str) -> None:
        footer_rect = self.rect().adjusted(14, self.height() - 22, -14, -6)
        footer_pen = QPen(QColor(85, 85, 85), 1.0)
        footer_pen.setCosmetic(True)
        painter.setPen(footer_pen)
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
        line_color = QColor(35, 160, 85)

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

            painter.fillRect(
                QRectF(left, rect.top(), 2.0, rect.height()),
                line_color,
            )

            if end_index is not None:
                painter.fillRect(
                    QRectF(max(left, right - 2), rect.top(), 2.0, rect.height()),
                    line_color,
                )

    def _draw_markers(
        self,
        painter: QPainter,
        rect: QRectF,
        visible_start: int,
        visible_end: int,
    ) -> None:
        if visible_end <= visible_start:
            return

        marker_pen = QPen(QColor("#D32F2F"), 1.6)
        marker_pen.setCosmetic(True)
        marker_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        label_pen = QPen(QColor("#B71C1C"), 1.0)
        label_pen.setCosmetic(True)

        for marker in self._markers:
            if marker.sample_index < visible_start or marker.sample_index > visible_end:
                continue

            marker_x = self._sample_to_x(rect, marker.sample_index, visible_start, visible_end)
            painter.setPen(marker_pen)
            painter.drawLine(QLineF(marker_x, rect.top(), marker_x, rect.bottom()))

            label_rect = QRectF(marker_x + 4, rect.top() + 4, 96, 18)
            painter.setPen(label_pen)
            painter.drawText(
                label_rect,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                marker.label,
            )

    def _draw_segment_regions(
        self,
        painter: QPainter,
        rect: QRectF,
        visible_start: int,
        visible_end: int,
    ) -> None:
        if visible_end <= visible_start:
            return

        fill_color = QColor(211, 47, 47, 28)
        line_color = QColor("#C62828")
        label_pen = QPen(QColor("#B71C1C"), 1.0)
        label_pen.setCosmetic(True)

        for start_index, end_index, label in self._segments:
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
            painter.fillRect(QRectF(left, rect.top(), 2.0, rect.height()), line_color)

            if end_index is not None:
                painter.fillRect(
                    QRectF(max(left, right - 2), rect.top(), 2.0, rect.height()),
                    line_color,
                )

            painter.setPen(label_pen)
            painter.drawText(
                QRectF(left + 6, rect.top() + 6, max(80.0, right - left - 12), 18),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                label,
            )

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

    def _is_channel_visible(self, index: int) -> bool:
        if index < len(self._channel_visibility):
            return self._channel_visibility[index]
        return True


class StreamPlotWidget(QFrame):
    def __init__(
        self,
        max_samples: int = 2000,
        display_settings: DisplaySettings | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self.max_samples = max_samples
        self.display_settings = display_settings
        self._is_paused = False
        self._current_state: str = DeviceState.DISCONNECTED.value
        self._device_name: str = "-"
        self._last_seq: int | None = None
        self._last_fs: float | None = None

        self.setObjectName("stream-plot-widget")
        self.setStyleSheet(
            f"""
            QFrame#stream-plot-widget {{
                background: rgba(255, 255, 255, 0.78);
                border: 1px solid rgba(0, 0, 0, 0.08);
                border-radius: {DEFAULT_RADIUS}px;
            }}
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
        if self.display_settings is not None:
            self.canvas.set_max_samples(self.display_settings.max_samples)
            self.canvas.set_channel_visibility(self.display_settings.channel_visibility)
            self.display_settings.maxSamplesChanged.connect(self._on_max_samples_changed)
            self.display_settings.channelVisibilityChanged.connect(
                self._on_channel_visibility_changed
            )

        root_layout.addWidget(self.title_label)
        root_layout.addWidget(self.status_label)
        root_layout.addWidget(self.canvas, 1)
        self._update_status_text()

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

    def add_marker(self, event: MarkerEvent) -> None:
        self.canvas.add_marker(event)
        self._update_status_text()

    def update_segment_state(self, event: SegmentEvent) -> None:
        self.canvas.update_segment_state(event)
        self._update_status_text()

    def set_paused(self, is_paused: bool) -> None:
        if self._is_paused == is_paused:
            return

        self._is_paused = is_paused
        self.canvas.set_paused(is_paused)
        self._update_status_text()

    def _on_max_samples_changed(self, max_samples: int) -> None:
        self.max_samples = max_samples
        self.canvas.set_max_samples(max_samples)
        self._update_status_text()

    def _on_channel_visibility_changed(self, visibility: tuple[bool, ...]) -> None:
        self.canvas.set_channel_visibility(visibility)
        self._update_status_text()

    def _update_status_text(self) -> None:
        visible_count = self._visible_channel_count()
        total_channels = self._total_channel_count()
        display_info = f"显示: {visible_count}/{total_channels} ch | 点数: {self.max_samples}"
        pause_info = " | 显示已暂停" if self._is_paused else ""

        if self.canvas.has_samples and self._last_seq is not None and self._last_fs is not None:
            self.status_label.setText(
                f"状态: {self._current_state} | 设备: {self._device_name} | "
                f"seq: {self._last_seq} | fs: {self._last_fs:.1f} Hz | {display_info}{pause_info}"
            )
            return

        self.status_label.setText(
            f"状态: {self._current_state} | 设备: {self._device_name} | "
            f"等待数据流，X 轴严格使用 sample_index0 | {display_info}{pause_info}"
        )

    def _visible_channel_count(self) -> int:
        if self.display_settings is None:
            return len(self.canvas.channel_names) or 4

        return sum(1 for value in self.display_settings.channel_visibility if value)

    def _total_channel_count(self) -> int:
        if self.display_settings is not None:
            return self.display_settings.n_channels

        return len(self.canvas.channel_names) or 4
