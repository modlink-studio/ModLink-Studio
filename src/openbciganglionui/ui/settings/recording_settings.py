from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal

from ...backend import RecordingMode


class RecordingSettings(QObject):
    recordingModeChanged = pyqtSignal(object)

    def __init__(
        self,
        recording_mode: RecordingMode = RecordingMode.CLIP,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self._recording_mode = self._normalize_mode(recording_mode)

    @property
    def recording_mode(self) -> RecordingMode:
        return self._recording_mode

    def set_recording_mode(self, value: RecordingMode | str) -> None:
        normalized = self._normalize_mode(value)
        if normalized == self._recording_mode:
            return

        self._recording_mode = normalized
        self.recordingModeChanged.emit(self._recording_mode)

    def _normalize_mode(self, value: RecordingMode | str) -> RecordingMode:
        if isinstance(value, RecordingMode):
            return value
        try:
            return RecordingMode(str(value).strip())
        except ValueError:
            return RecordingMode.CLIP
