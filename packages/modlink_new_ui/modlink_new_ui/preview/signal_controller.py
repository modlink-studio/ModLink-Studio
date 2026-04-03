from __future__ import annotations

import numpy as np
from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal
from PyQt6.QtGui import QImage

from modlink_sdk import FrameEnvelope, StreamDescriptor

from .models import SignalFilterSettings, SignalPreviewSettings
from .signal_filter import SignalFilterPipeline, SignalFilterSpec
from .signal_ring_buffer import SignalRingBuffer

SIGNAL_WINDOW_SECONDS_OPTIONS = (1, 2, 4, 8, 12, 20)
DEFAULT_SIGNAL_WINDOW_SECONDS = 8


class SignalStreamController(QObject):
    dataChanged = pyqtSignal()
    settingsChanged = pyqtSignal()

    def __init__(self, descriptor: StreamDescriptor, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._descriptor = descriptor
        self._sample_rate_hz = max(1.0, float(descriptor.nominal_sample_rate_hz or 1.0))
        self._channel_names = list(descriptor.channel_names)
        self._settings = SignalPreviewSettings()
        self._ring_buffer: SignalRingBuffer | None = None
        self._max_samples = self._compute_max_samples(self._settings.window_seconds)
        self._filter_spec = self._to_filter_spec(self._settings.filter)
        self._pipeline = SignalFilterPipeline(sample_rate_hz=self._sample_rate_hz)
        self._pipeline.configure(self._filter_spec)
        self._has_frame = False

        self._channel_data: list[np.ndarray] = []

    @property
    def descriptor(self) -> StreamDescriptor:
        return self._descriptor

    @property
    def payload_type(self) -> str:
        return "signal"

    @property
    def has_frame(self) -> bool:
        return self._has_frame

    @pyqtProperty("QVariantList", notify=dataChanged)
    def channelData(self) -> list[object]:
        return self._channel_data

    @pyqtProperty("QVariantList", constant=True)
    def channelNames(self) -> list[str]:
        return self._channel_names

    @pyqtProperty(float, constant=True)
    def sampleRateHz(self) -> float:
        return self._sample_rate_hz

    @pyqtProperty(str, notify=settingsChanged)
    def layoutMode(self) -> str:
        return self._settings.layout_mode

    @pyqtProperty(str, notify=settingsChanged)
    def yRangeMode(self) -> str:
        return self._settings.y_range_mode

    @pyqtProperty(float, notify=settingsChanged)
    def manualYMin(self) -> float:
        return self._settings.manual_y_min

    @pyqtProperty(float, notify=settingsChanged)
    def manualYMax(self) -> float:
        return self._settings.manual_y_max

    def apply_settings(self, settings: SignalPreviewSettings) -> None:
        old_filter = self._to_filter_spec(self._settings.filter)
        self._settings = settings
        new_max = self._compute_max_samples(settings.window_seconds)
        if new_max != self._max_samples:
            self._max_samples = new_max
            if self._ring_buffer is not None:
                self._ring_buffer.resize(new_max)

        new_filter = self._to_filter_spec(settings.filter)
        if new_filter != old_filter:
            self._filter_spec = new_filter
            self._pipeline.configure(self._filter_spec)
            self._pipeline.reset_states()
            if self._ring_buffer is not None:
                self._ring_buffer.clear()

        self._channel_names = list(self._descriptor.channel_names)
        self.settingsChanged.emit()

    def push_frame(self, frame: FrameEnvelope) -> None:
        data = np.asarray(frame.data)
        if data.ndim != 2:
            return
        ch_count, chunk_size = int(data.shape[0]), int(data.shape[1])
        if ch_count <= 0 or chunk_size <= 0:
            return

        self._ensure_ring_buffer(ch_count)
        processed = self._pipeline.process(np.asarray(data, dtype=np.float32))
        if self._ring_buffer is not None:
            self._ring_buffer.extend(processed)
        self._has_frame = True

    def flush(self) -> bool:
        if self._ring_buffer is None or not self._has_frame:
            return False
        linear = self._ring_buffer.get_linear()
        if linear.size == 0:
            return False

        ch_count = int(linear.shape[0])
        vci = self._effective_visible_channels(ch_count)
        self._channel_data = [linear[i].copy() for i in vci]
        self.dataChanged.emit()
        return True

    def _ensure_ring_buffer(self, ch_count: int) -> None:
        if self._ring_buffer is not None and self._ring_buffer.channels == ch_count:
            return
        self._ring_buffer = SignalRingBuffer(ch_count, self._max_samples)
        if ch_count > len(self._channel_names):
            self._channel_names = [
                self._channel_names[i] if i < len(self._channel_names) else f"ch{i + 1}"
                for i in range(ch_count)
            ]

    def _effective_visible_channels(self, ch_count: int) -> tuple[int, ...]:
        if ch_count <= 0:
            return ()
        vci = tuple(i for i in self._settings.visible_channel_indices if 0 <= i < ch_count)
        return vci or tuple(range(ch_count))

    def _compute_max_samples(self, window_seconds: int) -> int:
        return max(
            int(self._sample_rate_hz * window_seconds),
            int(self._descriptor.chunk_size) * 24,
            512,
        )

    @staticmethod
    def _to_filter_spec(f: SignalFilterSettings) -> SignalFilterSpec:
        return SignalFilterSpec(
            family=f.family,
            mode=f.mode,
            order=f.order,
            low_cutoff_hz=f.low_cutoff_hz,
            high_cutoff_hz=f.high_cutoff_hz,
            notch_enabled=f.notch_enabled,
            notch_frequencies_hz=f.notch_frequencies_hz,
            notch_q=f.notch_q,
            chebyshev1_ripple_db=f.chebyshev1_ripple_db,
        )
