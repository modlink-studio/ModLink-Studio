from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal


class DisplaySettings(QObject):
    maxSamplesChanged = pyqtSignal(int)
    channelVisibilityChanged = pyqtSignal(tuple)

    def __init__(
        self,
        max_samples: int = 2000,
        n_channels: int = 4,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self._n_channels = max(1, int(n_channels))
        self._max_samples = max(1, int(max_samples))
        self._channel_visibility = [True] * self._n_channels

    @property
    def max_samples(self) -> int:
        return self._max_samples

    @property
    def n_channels(self) -> int:
        return self._n_channels

    @property
    def channel_visibility(self) -> tuple[bool, ...]:
        return tuple(self._channel_visibility)

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
