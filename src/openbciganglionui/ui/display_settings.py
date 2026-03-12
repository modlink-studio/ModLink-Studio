from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal


class DisplaySettings(QObject):
    maxSamplesChanged = pyqtSignal(int)
    channelVisibilityChanged = pyqtSignal(tuple)
    yAxisAutoChanged = pyqtSignal(bool)
    yAxisBoundsChanged = pyqtSignal(float, float)
    plotHeightChanged = pyqtSignal(int)

    def __init__(
        self,
        max_samples: int = 2000,
        n_channels: int = 4,
        y_axis_auto: bool = True,
        y_axis_lower: float = -100.0,
        y_axis_upper: float = 100.0,
        plot_height: int = 380,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self._n_channels = max(1, int(n_channels))
        self._max_samples = max(1, int(max_samples))
        self._channel_visibility = [True] * self._n_channels
        self._y_axis_auto = bool(y_axis_auto)
        self._y_axis_lower = float(y_axis_lower)
        self._y_axis_upper = float(y_axis_upper)
        self._plot_height = max(260, int(plot_height))

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

    def is_channel_visible(self, index: int) -> bool:
        if 0 <= index < self._n_channels:
            return self._channel_visibility[index]
        return True

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
