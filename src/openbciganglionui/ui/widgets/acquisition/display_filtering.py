from __future__ import annotations

import numpy as np
from brainflow.data_filter import DataFilter, FilterTypes

from ...settings import ChannelFilterConfig


_MIN_FILTER_SAMPLES = 8


def apply_channel_filter(
    values: np.ndarray,
    sampling_rate_hz: float | None,
    config: ChannelFilterConfig,
    filter_family: str,
    filter_order: int,
) -> np.ndarray:
    if config.mode == "none" and config.powerline_mode == "none":
        return values
    if sampling_rate_hz is None or sampling_rate_hz <= 0:
        return values
    if values.size < _MIN_FILTER_SAMPLES:
        return values

    numeric_values = np.asarray(values, dtype=np.float64).copy()
    sampling_rate = max(1, int(round(float(sampling_rate_hz))))
    nyquist_hz = float(sampling_rate_hz) * 0.5
    if nyquist_hz <= 0:
        return values

    filter_type = _resolve_filter_type(filter_family)
    ripple = _resolve_ripple(filter_family)

    try:
        if config.mode == "lowpass":
            cutoff_hz = min(max(0.1, float(config.high_cut_hz)), nyquist_hz - 0.1)
            if cutoff_hz > 0:
                DataFilter.perform_lowpass(
                    numeric_values,
                    sampling_rate,
                    cutoff_hz,
                    int(filter_order),
                    filter_type,
                    ripple,
                )
        elif config.mode == "highpass":
            cutoff_hz = min(max(0.1, float(config.low_cut_hz)), nyquist_hz - 0.1)
            if cutoff_hz > 0:
                DataFilter.perform_highpass(
                    numeric_values,
                    sampling_rate,
                    cutoff_hz,
                    int(filter_order),
                    filter_type,
                    ripple,
                )
        elif config.mode == "bandpass":
            low_cut_hz = min(max(0.1, float(config.low_cut_hz)), nyquist_hz - 0.2)
            high_cut_hz = min(max(0.1, float(config.high_cut_hz)), nyquist_hz - 0.1)
            if high_cut_hz <= low_cut_hz:
                return values
            DataFilter.perform_bandpass(
                numeric_values,
                sampling_rate,
                low_cut_hz,
                high_cut_hz,
                int(filter_order),
                filter_type,
                ripple,
            )

        half_width_hz = max(0.5, float(config.notch_width_hz) * 0.5)
        for center_hz in _powerline_centers(config.powerline_mode):
            if center_hz >= nyquist_hz:
                continue
            lower_hz = max(0.1, center_hz - half_width_hz)
            upper_hz = min(nyquist_hz - 0.1, center_hz + half_width_hz)
            if upper_hz <= lower_hz:
                continue
            DataFilter.perform_bandstop(
                numeric_values,
                sampling_rate,
                lower_hz,
                upper_hz,
                int(filter_order),
                filter_type,
                ripple,
            )
    except Exception:
        return values

    return numeric_values.astype(np.float32, copy=False)


def _powerline_centers(powerline_mode: str) -> tuple[float, ...]:
    if powerline_mode == "hz50":
        return (50.0,)
    if powerline_mode == "hz60":
        return (60.0,)
    if powerline_mode == "hz50_60":
        return (50.0, 60.0)
    return ()


def _resolve_filter_type(filter_family: str) -> int:
    if filter_family == "butterworth":
        return int(FilterTypes.BUTTERWORTH)
    if filter_family == "chebyshev1":
        return int(FilterTypes.CHEBYSHEV_TYPE_1)
    if filter_family == "bessel":
        return int(FilterTypes.BESSEL)
    if filter_family == "butterworth_zero_phase":
        return int(FilterTypes.BUTTERWORTH_ZERO_PHASE)
    if filter_family == "chebyshev1_zero_phase":
        return int(FilterTypes.CHEBYSHEV_TYPE_1_ZERO_PHASE)
    if filter_family == "bessel_zero_phase":
        return int(FilterTypes.BESSEL_ZERO_PHASE)
    return int(FilterTypes.BUTTERWORTH)


def _resolve_ripple(filter_family: str) -> float:
    if filter_family in {"chebyshev1", "chebyshev1_zero_phase"}:
        return 1.0
    return 0.0
