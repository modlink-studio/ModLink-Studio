from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Literal

import numpy as np
from PyQt6.QtWidgets import QVBoxLayout

import pyqtgraph as pg
from scipy import signal as sp_signal

from modlink_sdk import FrameEnvelope, StreamDescriptor

from .base import BaseStreamView

DEFAULT_SIGNAL_WINDOW_SECONDS = 8
SIGNAL_WINDOW_SECONDS_OPTIONS = (1, 2, 4, 8, 12, 20)


@dataclass(slots=True)
class _SignalFilterSpec:
    family: Literal["butterworth", "chebyshev1", "bessel"] = "butterworth"
    mode: Literal["none", "low_pass", "high_pass", "band_pass", "band_stop"] = "none"
    order: int = 4
    low_cutoff_hz: float = 1.0
    high_cutoff_hz: float = 40.0
    notch_enabled: bool = False
    notch_frequencies_hz: tuple[float, ...] = ()
    notch_q: float = 30.0
    chebyshev1_ripple_db: float = 1.0


class _SignalFilterPipeline:
    def __init__(self, sample_rate_hz: float) -> None:
        self.sample_rate_hz = max(1.0, float(sample_rate_hz))
        self._main_sos: np.ndarray | None = None
        self._notch_sos: list[np.ndarray] = []
        self._main_states: list[np.ndarray] = []
        self._notch_states: list[list[np.ndarray]] = []
        self._channel_count = 0

    def configure(self, spec: _SignalFilterSpec) -> None:
        self._main_sos = self._design_main_sos(spec)
        self._notch_sos = self._design_notch_sos(spec)
        self.reset_states()

    def reset_states(self) -> None:
        self._channel_count = 0
        self._main_states = []
        self._notch_states = []

    def process(self, data: np.ndarray) -> np.ndarray:
        if data.ndim != 2:
            return data
        channel_count = int(data.shape[0])
        if channel_count <= 0:
            return data
        self._ensure_channel_states(channel_count)

        output = np.empty_like(data, dtype=np.float32)
        for channel_index in range(channel_count):
            values = np.asarray(data[channel_index], dtype=np.float64)
            if self._main_sos is not None:
                values, self._main_states[channel_index] = sp_signal.sosfilt(
                    self._main_sos,
                    values,
                    zi=self._main_states[channel_index],
                )
            if self._notch_sos:
                notch_states = self._notch_states[channel_index]
                for notch_index, notch_sos in enumerate(self._notch_sos):
                    values, notch_states[notch_index] = sp_signal.sosfilt(
                        notch_sos,
                        values,
                        zi=notch_states[notch_index],
                    )
            output[channel_index] = values.astype(np.float32, copy=False)
        return output

    def _ensure_channel_states(self, channel_count: int) -> None:
        if channel_count == self._channel_count:
            return
        self._channel_count = channel_count

        main_sections = int(self._main_sos.shape[0]) if self._main_sos is not None else 0
        self._main_states = [
            np.zeros((main_sections, 2), dtype=np.float64) for _ in range(channel_count)
        ]

        self._notch_states = []
        for _ in range(channel_count):
            channel_states = [
                np.zeros((int(notch_sos.shape[0]), 2), dtype=np.float64)
                for notch_sos in self._notch_sos
            ]
            self._notch_states.append(channel_states)

    def _design_main_sos(self, spec: _SignalFilterSpec) -> np.ndarray | None:
        if spec.mode == "none":
            return None

        nyquist = self.sample_rate_hz * 0.5
        if nyquist <= 0:
            return None

        btype_map = {
            "low_pass": "lowpass",
            "high_pass": "highpass",
            "band_pass": "bandpass",
            "band_stop": "bandstop",
        }
        btype = btype_map.get(spec.mode)
        if btype is None:
            return None

        low = max(1e-6, min(float(spec.low_cutoff_hz), nyquist - 1e-6))
        high = max(1e-6, min(float(spec.high_cutoff_hz), nyquist - 1e-6))
        if spec.mode in {"band_pass", "band_stop"}:
            if low >= high:
                return None
            wn: float | tuple[float, float] = (low, high)
        else:
            wn = low

        try:
            if spec.family == "butterworth":
                return sp_signal.butter(
                    N=int(spec.order),
                    Wn=wn,
                    btype=btype,
                    fs=self.sample_rate_hz,
                    output="sos",
                )
            if spec.family == "chebyshev1":
                return sp_signal.cheby1(
                    N=int(spec.order),
                    rp=max(0.01, float(spec.chebyshev1_ripple_db)),
                    Wn=wn,
                    btype=btype,
                    fs=self.sample_rate_hz,
                    output="sos",
                )
            if spec.family == "bessel":
                return sp_signal.bessel(
                    N=int(spec.order),
                    Wn=wn,
                    btype=btype,
                    fs=self.sample_rate_hz,
                    output="sos",
                    norm="phase",
                )
        except ValueError:
            return None
        return None

    def _design_notch_sos(self, spec: _SignalFilterSpec) -> list[np.ndarray]:
        if not spec.notch_enabled:
            return []
        nyquist = self.sample_rate_hz * 0.5
        if nyquist <= 0:
            return []

        result: list[np.ndarray] = []
        for frequency in spec.notch_frequencies_hz:
            hz = float(frequency)
            if hz <= 0.0 or hz >= nyquist:
                continue
            normalized = hz / nyquist
            if normalized <= 0.0 or normalized >= 1.0:
                continue
            try:
                b, a = sp_signal.iirnotch(normalized, max(0.1, float(spec.notch_q)))
                result.append(sp_signal.tf2sos(b, a))
            except ValueError:
                continue
        return result


class SignalStreamView(BaseStreamView):
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
        parent=None,
    ) -> None:
        super().__init__(descriptor, parent=parent)

        self._sample_rate_hz = max(1.0, float(descriptor.nominal_sample_rate_hz or 1.0))
        self._window_seconds = DEFAULT_SIGNAL_WINDOW_SECONDS
        self._max_samples = self._compute_max_samples(self._window_seconds)
        self._channel_names = tuple(descriptor.channel_names)
        self._buffers: list[deque[float]] = []
        self._curves: list[object] = []
        self._antialias_enabled = True
        self._auto_downsample_enabled = False
        self._filter_spec = _SignalFilterSpec()
        self._pipeline = _SignalFilterPipeline(sample_rate_hz=self._sample_rate_hz)
        self._pipeline.configure(self._filter_spec)

        self._plot_widget = pg.PlotWidget(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._plot_widget, 1)
        self._configure_plot()

        self.setMinimumHeight(260)

    @property
    def window_seconds(self) -> int:
        return self._window_seconds

    def apply_preview_settings(self, settings: object) -> None:
        window_seconds = self._coerce_int(
            getattr(settings, "window_seconds", self._window_seconds),
            fallback=self._window_seconds,
        )
        self._apply_window_seconds(window_seconds)
        self._antialias_enabled = bool(
            getattr(settings, "antialias_enabled", self._antialias_enabled)
        )
        self._auto_downsample_enabled = bool(
            getattr(
                settings,
                "auto_downsample_enabled",
                self._auto_downsample_enabled,
            )
        )
        self._apply_render_quality()

        next_spec = self._extract_filter_spec(settings)
        if next_spec != self._filter_spec:
            self._filter_spec = next_spec
            self._pipeline.configure(self._filter_spec)
            self._reset_signal_state()

    def _compute_max_samples(self, window_seconds: int) -> int:
        return max(
            int(self._sample_rate_hz * window_seconds),
            int(self.descriptor.chunk_size) * 24,
            512,
        )

    def _apply_window_seconds(self, window_seconds: int) -> None:
        if window_seconds not in SIGNAL_WINDOW_SECONDS_OPTIONS:
            window_seconds = DEFAULT_SIGNAL_WINDOW_SECONDS
        self._window_seconds = window_seconds
        max_samples = self._compute_max_samples(window_seconds)
        if max_samples == self._max_samples:
            return

        self._max_samples = max_samples
        if self._buffers:
            self._buffers = [
                deque(list(buffer)[-self._max_samples :], maxlen=self._max_samples)
                for buffer in self._buffers
            ]

        if self.has_frame:
            self._dirty = True

    def _configure_plot(self) -> None:
        assert self._plot_widget is not None
        self._plot_widget.setBackground("transparent")
        self._plot_widget.showGrid(x=True, y=True, alpha=0.16)
        self._plot_widget.setMenuEnabled(False)
        self._plot_widget.setMouseEnabled(x=False, y=False)
        self._plot_widget.hideButtons()
        self._plot_widget.setAntialiasing(self._antialias_enabled)

        plot_item = self._plot_widget.getPlotItem()
        plot_item.setClipToView(True)
        plot_item.setDownsampling(
            ds=1,
            auto=self._auto_downsample_enabled,
            mode="peak",
        )
        plot_item.setLabel("bottom", "时间", units="s")

    def _apply_render_quality(self) -> None:
        self._plot_widget.setAntialiasing(self._antialias_enabled)
        plot_item = self._plot_widget.getPlotItem()
        plot_item.setDownsampling(
            ds=1,
            auto=self._auto_downsample_enabled,
            mode="peak",
        )
        for curve in self._curves:
            curve.opts["antialias"] = self._antialias_enabled
            curve.setDownsampling(
                ds=1,
                auto=self._auto_downsample_enabled,
                method="peak",
            )
            curve.setClipToView(self._auto_downsample_enabled)
            curve.updateItems(styleUpdate=True)
        if self.has_frame:
            self._dirty = True

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
                antialias=self._antialias_enabled,
                autoDownsample=self._auto_downsample_enabled,
                downsample=1,
                downsampleMethod="peak",
                clipToView=self._auto_downsample_enabled,
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
        processed = self._pipeline.process(np.asarray(data, dtype=np.float32))
        for channel_index in range(channel_count):
            self._buffers[channel_index].extend(
                np.asarray(processed[channel_index], dtype=np.float32).tolist()
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

    def _reset_signal_state(self) -> None:
        self._pipeline.reset_states()
        for buffer in self._buffers:
            buffer.clear()
        if self.has_frame:
            self._dirty = True

    def _extract_filter_spec(self, settings: object) -> _SignalFilterSpec:
        nyquist = max(self._sample_rate_hz * 0.5, 1.0)
        filter_settings = getattr(settings, "filter", None)
        if filter_settings is None:
            return _SignalFilterSpec()

        mode = self._coerce_str(
            self._read_attr(filter_settings, "mode", "none"),
            fallback="none",
        )
        family = self._coerce_str(
            self._read_attr(filter_settings, "family", "butterworth"),
            fallback="butterworth",
        )
        mode = mode if mode in {"none", "low_pass", "high_pass", "band_pass", "band_stop"} else "none"
        family = family if family in {"butterworth", "chebyshev1", "bessel"} else "butterworth"

        order = max(
            1,
            min(
                12,
                self._coerce_int(
                    self._read_attr(filter_settings, "order", 4),
                    fallback=4,
                ),
            ),
        )
        low_cutoff = self._coerce_float(
            self._read_attr(filter_settings, "low_cutoff_hz", 1.0),
            fallback=1.0,
        )
        high_cutoff = self._coerce_float(
            self._read_attr(filter_settings, "high_cutoff_hz", 40.0),
            fallback=40.0,
        )
        max_cutoff = max(1e-6, nyquist - 1e-6)
        low_cutoff = min(max(1e-6, low_cutoff), max_cutoff)
        high_cutoff = min(max(1e-6, high_cutoff), max_cutoff)
        if mode in {"band_pass", "band_stop"} and low_cutoff >= high_cutoff:
            mode = "none"

        notch_enabled = bool(
            self._read_attr(
                filter_settings,
                "notch_enabled",
                False,
            )
        )
        raw_notches = self._read_attr(
            filter_settings,
            "notch_frequencies_hz",
            [],
        )
        if not isinstance(raw_notches, (list, tuple)):
            raw_notches = ()
        normalized_notches = tuple(
            sorted(
                {
                    round(self._coerce_float(value, fallback=0.0), 6)
                    for value in raw_notches
                    if 0.0 < self._coerce_float(value, fallback=0.0) < nyquist
                }
            )
        )

        notch_q = self._coerce_float(
            self._read_attr(filter_settings, "notch_q", 30.0),
            fallback=30.0,
        )
        ripple = self._coerce_float(
            self._read_attr(filter_settings, "chebyshev1_ripple_db", 1.0),
            fallback=1.0,
        )

        return _SignalFilterSpec(
            family=family,
            mode=mode,
            order=order,
            low_cutoff_hz=low_cutoff,
            high_cutoff_hz=high_cutoff,
            notch_enabled=notch_enabled,
            notch_frequencies_hz=normalized_notches,
            notch_q=max(0.1, notch_q),
            chebyshev1_ripple_db=max(0.01, ripple),
        )

    @staticmethod
    def _read_attr(target: object, name: str, fallback: object) -> object:
        if target is None:
            return fallback
        return getattr(target, name, fallback)

    @staticmethod
    def _coerce_int(value: object, fallback: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return fallback

    @staticmethod
    def _coerce_float(value: object, fallback: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return fallback

    @staticmethod
    def _coerce_str(value: object, fallback: str) -> str:
        if not isinstance(value, str):
            return fallback
        return value
