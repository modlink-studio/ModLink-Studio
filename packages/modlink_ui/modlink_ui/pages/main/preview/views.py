from __future__ import annotations

from collections import deque

import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel

from modlink_sdk import FrameEnvelope, StreamDescriptor

from ....widgets.base import BaseStreamView, ImageStreamView

import pyqtgraph as pg


class UnavailableStreamView(BaseStreamView):
    def __init__(
        self,
        descriptor: StreamDescriptor,
        *,
        reason: str,
        parent: QWidget | None = None,
    ) -> None:
        self._reason = reason
        super().__init__(descriptor, parent=parent)
        self._body = BodyLabel(reason, self)
        self._body.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.addStretch(1)
        layout.addWidget(self._body, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addStretch(1)

        self.setMinimumHeight(220)

    def _ingest_frame(self, frame: FrameEnvelope) -> bool:
        return False

    def _render(self) -> None:
        return


class LineStreamView(BaseStreamView):
    _colors = (
        "#2D8CF0",
        "#19BE6B",
        "#FF9F43",
        "#E74C3C",
        "#8E44AD",
        "#16A085",
        "#34495E",
        "#D35400",
    )

    def __init__(
        self,
        descriptor: StreamDescriptor,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(descriptor, parent=parent)

        sample_rate_hz = max(1.0, float(descriptor.nominal_sample_rate_hz or 1.0))
        self._sample_rate_hz = sample_rate_hz
        self._max_samples = max(
            int(sample_rate_hz * 8),
            int(descriptor.chunk_size) * 24,
            512,
        )
        self._channel_names = tuple(descriptor.channel_names)
        self._buffers: list[deque[float]] = []
        self._curves: list[object] = []

        self._plot_widget = pg.PlotWidget(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._plot_widget, 1)
        self._configure_plot()

        self.setMinimumHeight(260)

    def _configure_plot(self) -> None:
        assert self._plot_widget is not None
        self._plot_widget.setBackground("transparent")
        self._plot_widget.showGrid(x=True, y=True, alpha=0.16)
        self._plot_widget.setMenuEnabled(False)
        self._plot_widget.setMouseEnabled(x=False, y=False)
        self._plot_widget.hideButtons()
        self._plot_widget.setAntialiasing(False)

        plot_item = self._plot_widget.getPlotItem()
        plot_item.setClipToView(True)
        plot_item.setDownsampling(auto=True, mode="peak")
        plot_item.setLabel("bottom", "时间", units="s")

    def _ensure_channels(self, channel_count: int) -> None:
        if channel_count <= 0:
            return
        if len(self._buffers) == channel_count:
            return

        self._buffers = [deque(maxlen=self._max_samples) for _ in range(channel_count)]
        if len(self._channel_names) != channel_count:
            self._channel_names = tuple(
                f"ch{index + 1}" for index in range(channel_count)
            )

        plot_item = self._plot_widget.getPlotItem()
        for curve in self._curves:
            plot_item.removeItem(curve)
        self._curves.clear()

        for index in range(channel_count):
            curve = plot_item.plot(
                pen=pg.mkPen(self._colors[index % len(self._colors)], width=1.5),
            )
            self._curves.append(curve)

    def _ingest_frame(self, frame: FrameEnvelope) -> bool:
        data = np.asarray(frame.data)
        if data.ndim != 2:
            return False

        channel_count, chunk_size = int(data.shape[0]), int(data.shape[1])
        if channel_count <= 0 or chunk_size <= 0:
            return False

        self._ensure_channels(channel_count)
        for channel_index in range(channel_count):
            self._buffers[channel_index].extend(
                np.asarray(data[channel_index], dtype=np.float32).tolist()
            )
        return True

    def _render(self) -> None:
        if not self._buffers:
            return

        arrays = [
            np.fromiter(buffer, dtype=np.float32) for buffer in self._buffers if buffer
        ]
        if not arrays:
            return

        sample_count = min(array.size for array in arrays)
        if sample_count <= 0:
            return

        trimmed = [array[-sample_count:] for array in arrays]
        time_axis = (
            np.arange(sample_count, dtype=np.float32) - float(sample_count - 1)
        ) / np.float32(self._sample_rate_hz)

        peak = max(
            float(np.percentile(np.abs(values), 95)) if values.size else 0.0
            for values in trimmed
        )
        spacing = max(peak * 3.5, 1.0)
        ticks: list[tuple[float, str]] = []
        top_offset = float((len(trimmed) - 1) * spacing)

        for index, values in enumerate(trimmed):
            offset = top_offset - float(index) * spacing
            self._curves[index].setData(time_axis, values + offset)
            label = (
                self._channel_names[index]
                if index < len(self._channel_names)
                else f"ch{index + 1}"
            )
            ticks.append((offset, label))

        plot_item = self._plot_widget.getPlotItem()
        plot_item.getAxis("left").setTicks([ticks])
        plot_item.setXRange(float(time_axis[0]), 0.0, padding=0.0)
        plot_item.setYRange(-spacing, top_offset + spacing, padding=0.02)


class PlaneStreamView(ImageStreamView):
    def _compose_image(self, latest: np.ndarray) -> np.ndarray:
        if latest.shape[0] == 1:
            return np.asarray(latest[0], dtype=np.float32)
        return np.asarray(np.mean(latest, axis=0), dtype=np.float32)


class VideoStreamView(ImageStreamView):
    def _compose_image(self, latest: np.ndarray) -> np.ndarray:
        if latest.shape[0] in {3, 4}:
            return np.moveaxis(np.asarray(latest), 0, -1)
        if latest.shape[0] == 1:
            return np.asarray(latest[0], dtype=np.float32)
        return np.asarray(latest[0], dtype=np.float32)


def create_stream_view(
    descriptor: StreamDescriptor,
    parent: QWidget | None = None,
) -> BaseStreamView:
    if descriptor.payload_type == "line":
        return LineStreamView(descriptor, parent=parent)
    if descriptor.payload_type == "plane":
        return PlaneStreamView(descriptor, parent=parent)
    if descriptor.payload_type == "video":
        return VideoStreamView(descriptor, parent=parent)

    return UnavailableStreamView(
        descriptor,
        reason=f"当前不支持 payload_type={descriptor.payload_type} 的预览。",
        parent=parent,
    )
