from __future__ import annotations

from typing import Iterable

import numpy as np

EMBEDDED_SIGNAL_PLOT_HEIGHT = 260
_AUTO_RANGE_PADDING_RATIO = 0.08
_AUTO_RANGE_MIN_PADDING = 1e-3


def resolve_signal_view_height(
    layout_mode: str,
    visible_channel_count: int,
    plot_height: int = EMBEDDED_SIGNAL_PLOT_HEIGHT,
) -> int:
    count = max(1, int(visible_channel_count))
    if layout_mode == "expanded":
        return int(max(1, int(plot_height)) * count)
    return max(1, int(plot_height))


def compute_signal_auto_range(values: np.ndarray) -> tuple[float, float]:
    finite_values = np.asarray(values, dtype=np.float32)
    if finite_values.size <= 0:
        return (-1.0, 1.0)

    finite_values = finite_values[np.isfinite(finite_values)]
    if finite_values.size <= 0:
        return (-1.0, 1.0)

    minimum = float(np.min(finite_values))
    maximum = float(np.max(finite_values))
    span = max(maximum - minimum, 1e-6)
    padding = max(span * _AUTO_RANGE_PADDING_RATIO, _AUTO_RANGE_MIN_PADDING)
    return (minimum - padding, maximum + padding)


def compute_stacked_signal_range(channel_values: np.ndarray) -> tuple[float, float]:
    return compute_signal_auto_range(np.asarray(channel_values))


def compute_expanded_signal_ranges(
    channel_values: Iterable[np.ndarray],
) -> list[tuple[float, float]]:
    return [compute_signal_auto_range(np.asarray(values)) for values in channel_values]
