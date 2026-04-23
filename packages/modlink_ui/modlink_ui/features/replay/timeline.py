from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QMouseEvent, QPainter, QPen
from PyQt6.QtWidgets import QToolTip, QWidget
from qfluentwidgets import isDarkTheme

from modlink_core.models import ReplayMarker, ReplaySegment


def format_time_ns(value: int) -> str:
    total_ms = max(0, int(value // 1_000_000))
    total_seconds, millis = divmod(total_ms, 1000)
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"
    return f"{minutes:02d}:{seconds:02d}.{millis:03d}"


class ReplayAnnotationTimeline(QWidget):
    _minimum_segment_width = 6.0

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.setObjectName("replay-annotation-timeline")
        self.setMouseTracking(True)
        self.setMinimumHeight(62)

        self._markers: tuple[ReplayMarker, ...] = ()
        self._segments: tuple[ReplaySegment, ...] = ()
        self._position_ns = 0
        self._duration_ns = 0
        self._active_marker_index = -1
        self._active_segment_index = -1
        self._marker_regions: list[QRectF] = []
        self._segment_regions: list[QRectF] = []
        self._marker_tooltips: list[str] = []
        self._segment_tooltips: list[str] = []
        self._track_rect = QRectF()
        self._playhead_x = 0.0
        self._last_tooltip_text = ""

    @property
    def active_marker_index(self) -> int:
        return self._active_marker_index

    @property
    def active_segment_index(self) -> int:
        return self._active_segment_index

    @property
    def marker_count(self) -> int:
        return len(self._markers)

    @property
    def segment_count(self) -> int:
        return len(self._segments)

    @property
    def duration_ns(self) -> int:
        return self._duration_ns

    def set_annotations(
        self,
        markers: tuple[ReplayMarker, ...],
        segments: tuple[ReplaySegment, ...],
    ) -> None:
        self._markers = markers
        self._segments = segments
        self._recompute_active_indices()
        self._refresh_geometry()
        self.update()

    def set_playback(self, position_ns: int, duration_ns: int) -> None:
        self._position_ns = max(0, int(position_ns))
        self._duration_ns = max(0, int(duration_ns))
        self._recompute_active_indices()
        self._refresh_geometry()
        self.update()

    def clear(self) -> None:
        self._markers = ()
        self._segments = ()
        self._position_ns = 0
        self._duration_ns = 0
        self._active_marker_index = -1
        self._active_segment_index = -1
        self._marker_regions = []
        self._segment_regions = []
        self._marker_tooltips = []
        self._segment_tooltips = []
        self._track_rect = QRectF()
        self._playhead_x = 0.0
        self._last_tooltip_text = ""
        self.update()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._refresh_geometry()

    def leaveEvent(self, event) -> None:
        self._last_tooltip_text = ""
        QToolTip.hideText()
        super().leaveEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        tooltip_text = self._tooltip_text_at(event.position())
        if tooltip_text is None:
            if self._last_tooltip_text:
                self._last_tooltip_text = ""
                QToolTip.hideText()
        elif tooltip_text != self._last_tooltip_text:
            self._last_tooltip_text = tooltip_text
            QToolTip.showText(event.globalPosition().toPoint(), tooltip_text, self)
        super().mouseMoveEvent(event)

    def paintEvent(self, _event) -> None:
        self._refresh_geometry()

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self._track_rect.isEmpty():
            return

        palette = _timeline_palette()
        painter.setPen(Qt.PenStyle.NoPen)

        for index, segment_rect in enumerate(self._segment_regions):
            color = (
                palette["segment_active"]
                if index == self._active_segment_index
                else palette["segment"]
            )
            painter.setBrush(color)
            painter.drawRoundedRect(segment_rect, 3.0, 3.0)

        painter.setBrush(palette["track_background"])
        painter.drawRoundedRect(self._track_rect, 4.0, 4.0)

        if self._duration_ns > 0:
            played_width = max(0.0, self._playhead_x - self._track_rect.left())
            played_rect = QRectF(self._track_rect)
            played_rect.setWidth(min(self._track_rect.width(), played_width))
            painter.setBrush(palette["track_fill"])
            painter.drawRoundedRect(played_rect, 4.0, 4.0)

        painter.setPen(Qt.PenStyle.NoPen)
        for index, marker_rect in enumerate(self._marker_regions):
            color = (
                palette["marker_active"]
                if index == self._active_marker_index
                else palette["marker"]
            )
            painter.setBrush(color)
            painter.drawEllipse(marker_rect)

        painter.setPen(QPen(palette["playhead"], 2.0))
        painter.drawLine(
            QPointF(self._playhead_x, self._track_rect.top() - 18.0),
            QPointF(self._playhead_x, self._track_rect.bottom() + 2.0),
        )

    def _refresh_geometry(self) -> None:
        content_rect = QRectF(self.rect()).adjusted(12.0, 10.0, -12.0, -10.0)
        if content_rect.width() <= 0 or content_rect.height() <= 0:
            self._track_rect = QRectF()
            self._marker_regions = []
            self._segment_regions = []
            self._marker_tooltips = []
            self._segment_tooltips = []
            self._playhead_x = 0.0
            return

        track_top = content_rect.bottom() - 12.0
        self._track_rect = QRectF(
            content_rect.left(),
            track_top,
            content_rect.width(),
            8.0,
        )
        self._playhead_x = self._position_to_x(self._position_ns)

        self._marker_regions = []
        self._segment_regions = []
        self._marker_tooltips = []
        self._segment_tooltips = []

        marker_center_y = self._track_rect.top() - 10.0
        segment_top = self._track_rect.top() - 24.0
        segment_height = 7.0

        for marker in self._markers:
            x = self._position_to_x(marker.timestamp_ns)
            self._marker_regions.append(QRectF(x - 4.0, marker_center_y - 4.0, 8.0, 8.0))
            self._marker_tooltips.append(_marker_tooltip_text(marker))

        for segment in self._segments:
            segment_rect = self._segment_rect(
                segment.start_ns,
                segment.end_ns,
                top=segment_top,
                height=segment_height,
            )
            self._segment_regions.append(segment_rect)
            self._segment_tooltips.append(_segment_tooltip_text(segment))

    def _segment_rect(self, start_ns: int, end_ns: int, *, top: float, height: float) -> QRectF:
        if self._track_rect.isEmpty():
            return QRectF()

        start_x = self._position_to_x(start_ns)
        end_x = self._position_to_x(end_ns)
        if end_x < start_x:
            start_x, end_x = end_x, start_x

        desired_width = end_x - start_x
        track_width = max(0.0, self._track_rect.width())
        if track_width <= 0.0:
            return QRectF()
        width = min(track_width, max(self._minimum_segment_width, desired_width))
        midpoint = (start_x + end_x) / 2.0
        left = midpoint - width / 2.0
        left = max(self._track_rect.left(), left)
        left = min(left, self._track_rect.right() - width)
        return QRectF(left, top, width, height)

    def _position_to_x(self, timestamp_ns: int) -> float:
        if self._track_rect.isEmpty():
            return 0.0
        if self._duration_ns <= 0:
            return self._track_rect.left()
        ratio = max(0.0, min(1.0, float(timestamp_ns) / float(self._duration_ns)))
        return self._track_rect.left() + self._track_rect.width() * ratio

    def _recompute_active_indices(self) -> None:
        self._active_marker_index = -1
        self._active_segment_index = -1

        for index, marker in enumerate(self._markers):
            if marker.timestamp_ns <= self._position_ns:
                self._active_marker_index = index

        for index, segment in enumerate(self._segments):
            if segment.start_ns <= self._position_ns <= segment.end_ns:
                self._active_segment_index = index
                break

    def _tooltip_text_at(self, position: QPointF) -> str | None:
        for rect, tooltip in zip(self._marker_regions, self._marker_tooltips, strict=False):
            if rect.contains(position):
                return tooltip
        for rect, tooltip in zip(self._segment_regions, self._segment_tooltips, strict=False):
            if rect.contains(position):
                return tooltip
        return None


def _marker_tooltip_text(marker: ReplayMarker) -> str:
    return f"Marker · {format_time_ns(marker.timestamp_ns)}\n{marker.label or '未命名 marker'}"


def _segment_tooltip_text(segment: ReplaySegment) -> str:
    return (
        f"Segment · {format_time_ns(segment.start_ns)} → {format_time_ns(segment.end_ns)}\n"
        f"{segment.label or '未命名 segment'}"
    )


def _timeline_palette() -> dict[str, QColor]:
    if isDarkTheme():
        return {
            "track_background": QColor(255, 255, 255, 30),
            "track_fill": QColor(48, 212, 201, 170),
            "segment": QColor(129, 140, 248, 115),
            "segment_active": QColor(56, 189, 248, 200),
            "marker": QColor(255, 255, 255, 170),
            "marker_active": QColor(94, 234, 212, 240),
            "playhead": QColor(248, 250, 252, 230),
        }
    return {
        "track_background": QColor(15, 23, 42, 36),
        "track_fill": QColor(14, 165, 233, 185),
        "segment": QColor(99, 102, 241, 110),
        "segment_active": QColor(6, 182, 212, 190),
        "marker": QColor(71, 85, 105, 170),
        "marker_active": QColor(14, 165, 233, 240),
        "playhead": QColor(15, 23, 42, 220),
    }


__all__ = ["ReplayAnnotationTimeline", "format_time_ns"]
