from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
from scipy import signal as sp_signal


@dataclass(slots=True)
class SignalFilterSpec:
    family: Literal["butterworth", "chebyshev1", "bessel"] = "butterworth"
    mode: Literal["none", "low_pass", "high_pass", "band_pass", "band_stop"] = "none"
    order: int = 4
    low_cutoff_hz: float = 1.0
    high_cutoff_hz: float = 40.0
    notch_enabled: bool = False
    notch_frequencies_hz: tuple[float, ...] = ()
    notch_q: float = 30.0
    chebyshev1_ripple_db: float = 1.0


class SignalFilterPipeline:
    def __init__(self, sample_rate_hz: float) -> None:
        self.sample_rate_hz = max(1.0, float(sample_rate_hz))
        self._main_sos: np.ndarray | None = None
        self._notch_sos: list[np.ndarray] = []
        self._main_states: list[np.ndarray] = []
        self._notch_states: list[list[np.ndarray]] = []
        self._channel_count = 0

    def configure(self, spec: SignalFilterSpec) -> None:
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
        for ch in range(channel_count):
            values = np.asarray(data[ch], dtype=np.float64)
            if self._main_sos is not None:
                values, self._main_states[ch] = sp_signal.sosfilt(
                    self._main_sos, values, zi=self._main_states[ch],
                )
            if self._notch_sos:
                notch_states = self._notch_states[ch]
                for ni, notch_sos in enumerate(self._notch_sos):
                    values, notch_states[ni] = sp_signal.sosfilt(
                        notch_sos, values, zi=notch_states[ni],
                    )
            output[ch] = values.astype(np.float32, copy=False)
        return output

    def _ensure_channel_states(self, channel_count: int) -> None:
        if channel_count == self._channel_count:
            return
        self._channel_count = channel_count
        main_sections = int(self._main_sos.shape[0]) if self._main_sos is not None else 0
        self._main_states = [
            np.zeros((main_sections, 2), dtype=np.float64) for _ in range(channel_count)
        ]
        self._notch_states = [
            [np.zeros((int(ns.shape[0]), 2), dtype=np.float64) for ns in self._notch_sos]
            for _ in range(channel_count)
        ]

    def _design_main_sos(self, spec: SignalFilterSpec) -> np.ndarray | None:
        if spec.mode == "none":
            return None
        nyquist = self.sample_rate_hz * 0.5
        if nyquist <= 0:
            return None

        btype_map = {
            "low_pass": "lowpass", "high_pass": "highpass",
            "band_pass": "bandpass", "band_stop": "bandstop",
        }
        btype = btype_map.get(spec.mode)
        if btype is None:
            return None

        lo = max(1e-6, min(float(spec.low_cutoff_hz), nyquist - 1e-6))
        hi = max(1e-6, min(float(spec.high_cutoff_hz), nyquist - 1e-6))
        wn: float | tuple[float, float]
        if spec.mode in ("band_pass", "band_stop"):
            if lo >= hi:
                return None
            wn = (lo, hi)
        else:
            wn = lo

        try:
            if spec.family == "butterworth":
                return sp_signal.butter(N=int(spec.order), Wn=wn, btype=btype, fs=self.sample_rate_hz, output="sos")
            if spec.family == "chebyshev1":
                return sp_signal.cheby1(N=int(spec.order), rp=max(0.01, float(spec.chebyshev1_ripple_db)), Wn=wn, btype=btype, fs=self.sample_rate_hz, output="sos")
            if spec.family == "bessel":
                return sp_signal.bessel(N=int(spec.order), Wn=wn, btype=btype, fs=self.sample_rate_hz, output="sos", norm="phase")
        except ValueError:
            return None
        return None

    def _design_notch_sos(self, spec: SignalFilterSpec) -> list[np.ndarray]:
        if not spec.notch_enabled:
            return []
        nyquist = self.sample_rate_hz * 0.5
        if nyquist <= 0:
            return []
        result: list[np.ndarray] = []
        for freq in spec.notch_frequencies_hz:
            hz = float(freq)
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
