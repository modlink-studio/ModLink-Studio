from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from PyQt6.QtCore import QObject, pyqtSignal


@dataclass(frozen=True, slots=True)
class ChannelFilterConfig:
    mode: str = "none"
    low_cut_hz: float = 1.0
    high_cut_hz: float = 40.0
    powerline_mode: str = "none"
    notch_width_hz: float = 4.0

    def to_dict(self) -> dict[str, float | str]:
        return {
            "mode": self.mode,
            "low_cut_hz": float(self.low_cut_hz),
            "high_cut_hz": float(self.high_cut_hz),
            "powerline_mode": self.powerline_mode,
            "notch_width_hz": float(self.notch_width_hz),
        }


class DisplaySettings(QObject):
    maxSamplesChanged = pyqtSignal(int)
    channelVisibilityChanged = pyqtSignal(tuple)
    yAxisAutoChanged = pyqtSignal(bool)
    yAxisBoundsChanged = pyqtSignal(float, float)
    plotHeightChanged = pyqtSignal(int)
    filterSettingsChanged = pyqtSignal()

    def __init__(
        self,
        max_samples: int = 2000,
        n_channels: int = 4,
        channel_visibility: list[bool] | tuple[bool, ...] | None = None,
        y_axis_auto: bool = True,
        y_axis_lower: float = -100.0,
        y_axis_upper: float = 100.0,
        plot_height: int = 380,
        filter_family: str = "butterworth",
        filter_order: int = 4,
        shared_filter_enabled: bool = False,
        shared_filter: ChannelFilterConfig | dict[str, Any] | None = None,
        channel_filters: list[ChannelFilterConfig | dict[str, Any]] | tuple[ChannelFilterConfig | dict[str, Any], ...] | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self._n_channels = max(1, int(n_channels))
        self._max_samples = max(1, int(max_samples))
        self._channel_visibility = self._normalize_channel_visibility(channel_visibility)
        self._y_axis_auto = bool(y_axis_auto)
        self._y_axis_lower = float(y_axis_lower)
        self._y_axis_upper = float(y_axis_upper)
        self._plot_height = max(260, int(plot_height))
        self._filter_family = self._normalize_filter_family(filter_family)
        self._filter_order = self._normalize_filter_order(filter_order)
        self._shared_filter_enabled = bool(shared_filter_enabled)
        self._shared_filter = self._normalize_filter_config(shared_filter)
        self._channel_filters = self._normalize_channel_filters(channel_filters)

    @property
    def max_samples(self) -> int:
        return self._max_samples

    @property
    def n_channels(self) -> int:
        return self._n_channels

    @property
    def channel_visibility(self) -> tuple[bool, ...]:
        return tuple(self._channel_visibility)

    @property
    def y_axis_auto(self) -> bool:
        return self._y_axis_auto

    @property
    def y_axis_lower(self) -> float:
        return self._y_axis_lower

    @property
    def y_axis_upper(self) -> float:
        return self._y_axis_upper

    @property
    def plot_height(self) -> int:
        return self._plot_height

    @property
    def filter_family(self) -> str:
        return self._filter_family

    @property
    def filter_order(self) -> int:
        return self._filter_order

    @property
    def shared_filter_enabled(self) -> bool:
        return self._shared_filter_enabled

    @property
    def shared_filter_config(self) -> ChannelFilterConfig:
        return self._shared_filter

    @property
    def channel_filter_configs(self) -> tuple[ChannelFilterConfig, ...]:
        return tuple(self._channel_filters)

    def is_channel_visible(self, index: int) -> bool:
        if 0 <= index < self._n_channels:
            return self._channel_visibility[index]
        return True

    def channel_filter_config(self, index: int) -> ChannelFilterConfig:
        if 0 <= index < self._n_channels:
            return self._channel_filters[index]
        return ChannelFilterConfig()

    def effective_filter_config(self, index: int) -> ChannelFilterConfig:
        if self._shared_filter_enabled:
            return self._shared_filter
        return self.channel_filter_config(index)

    def set_max_samples(self, value: int) -> None:
        normalized = max(1, int(value))
        if normalized == self._max_samples:
            return

        self._max_samples = normalized
        self.maxSamplesChanged.emit(self._max_samples)

    def set_channel_visible(self, index: int, is_visible: bool) -> None:
        if not 0 <= index < self._n_channels:
            return

        normalized = bool(is_visible)
        if self._channel_visibility[index] == normalized:
            return

        self._channel_visibility[index] = normalized
        self.channelVisibilityChanged.emit(self.channel_visibility)

    def set_y_axis_auto(self, is_auto: bool) -> None:
        normalized = bool(is_auto)
        if self._y_axis_auto == normalized:
            return

        self._y_axis_auto = normalized
        self.yAxisAutoChanged.emit(self._y_axis_auto)

    def set_y_axis_bounds(self, lower: float, upper: float) -> None:
        normalized_lower = float(lower)
        normalized_upper = float(upper)
        if normalized_lower >= normalized_upper:
            return

        if (
            self._y_axis_lower == normalized_lower
            and self._y_axis_upper == normalized_upper
        ):
            return

        self._y_axis_lower = normalized_lower
        self._y_axis_upper = normalized_upper
        self.yAxisBoundsChanged.emit(self._y_axis_lower, self._y_axis_upper)

    def set_y_axis_lower(self, lower: float) -> None:
        self.set_y_axis_bounds(lower, self._y_axis_upper)

    def set_y_axis_upper(self, upper: float) -> None:
        self.set_y_axis_bounds(self._y_axis_lower, upper)

    def set_plot_height(self, height: int) -> None:
        normalized = max(260, int(height))
        if normalized == self._plot_height:
            return

        self._plot_height = normalized
        self.plotHeightChanged.emit(self._plot_height)

    def set_filter_family(self, family: str) -> None:
        normalized = self._normalize_filter_family(family)
        if normalized == self._filter_family:
            return

        self._filter_family = normalized
        self.filterSettingsChanged.emit()

    def set_filter_order(self, order: int) -> None:
        normalized = self._normalize_filter_order(order)
        if normalized == self._filter_order:
            return

        self._filter_order = normalized
        self.filterSettingsChanged.emit()

    def set_shared_filter_enabled(self, is_enabled: bool) -> None:
        normalized = bool(is_enabled)
        if normalized == self._shared_filter_enabled:
            return

        self._shared_filter_enabled = normalized
        self.filterSettingsChanged.emit()

    def set_shared_filter_config(
        self,
        config: ChannelFilterConfig | dict[str, Any],
    ) -> None:
        normalized = self._normalize_filter_config(config)
        if normalized == self._shared_filter:
            return

        self._shared_filter = normalized
        self.filterSettingsChanged.emit()

    def set_channel_filter_config(
        self,
        index: int,
        config: ChannelFilterConfig | dict[str, Any],
    ) -> None:
        if not 0 <= index < self._n_channels:
            return

        normalized = self._normalize_filter_config(config)
        if normalized == self._channel_filters[index]:
            return

        self._channel_filters[index] = normalized
        self.filterSettingsChanged.emit()

    def _normalize_channel_visibility(
        self,
        channel_visibility: list[bool] | tuple[bool, ...] | None,
    ) -> list[bool]:
        normalized = [True] * self._n_channels
        if channel_visibility is None:
            return normalized

        for index, value in enumerate(channel_visibility):
            if index >= self._n_channels:
                break
            normalized[index] = bool(value)
        return normalized

    def _normalize_channel_filters(
        self,
        channel_filters: list[ChannelFilterConfig | dict[str, Any]] | tuple[ChannelFilterConfig | dict[str, Any], ...] | None,
    ) -> list[ChannelFilterConfig]:
        normalized = [ChannelFilterConfig() for _ in range(self._n_channels)]
        if channel_filters is None:
            return normalized

        for index, value in enumerate(channel_filters):
            if index >= self._n_channels:
                break
            normalized[index] = self._normalize_filter_config(value)
        return normalized

    def _normalize_filter_config(
        self,
        config: ChannelFilterConfig | dict[str, Any] | None,
    ) -> ChannelFilterConfig:
        if isinstance(config, ChannelFilterConfig):
            payload = config.to_dict()
        else:
            payload = config if isinstance(config, dict) else {}

        mode = self._normalize_filter_mode(payload.get("mode"))
        powerline_mode = self._normalize_powerline_mode(payload.get("powerline_mode"))
        if mode == "notch50":
            mode = "none"
            powerline_mode = "hz50"
        elif mode == "notch60":
            mode = "none"
            powerline_mode = "hz60"

        return ChannelFilterConfig(
            mode=mode,
            low_cut_hz=self._normalize_positive_float(payload.get("low_cut_hz"), 1.0),
            high_cut_hz=self._normalize_positive_float(payload.get("high_cut_hz"), 40.0),
            powerline_mode=powerline_mode,
            notch_width_hz=self._normalize_positive_float(payload.get("notch_width_hz"), 4.0),
        )

    def _normalize_filter_mode(self, value: Any) -> str:
        normalized = str(value or "none").strip().lower()
        if normalized in {"none", "lowpass", "highpass", "bandpass", "notch50", "notch60"}:
            return normalized
        return "none"

    def _normalize_powerline_mode(self, value: Any) -> str:
        normalized = str(value or "none").strip().lower()
        if normalized in {"none", "hz50", "hz60", "hz50_60"}:
            return normalized
        return "none"

    def _normalize_positive_float(self, value: Any, default: float) -> float:
        try:
            normalized = float(value)
        except (TypeError, ValueError):
            normalized = default
        return max(0.1, normalized)

    def _normalize_filter_family(self, value: Any) -> str:
        normalized = str(value or "butterworth").strip().lower()
        if normalized in {
            "butterworth",
            "chebyshev1",
            "bessel",
            "butterworth_zero_phase",
            "chebyshev1_zero_phase",
            "bessel_zero_phase",
        }:
            return normalized
        return "butterworth"

    def _normalize_filter_order(self, value: Any) -> int:
        try:
            normalized = int(value)
        except (TypeError, ValueError):
            normalized = 4
        return max(1, min(8, normalized))
