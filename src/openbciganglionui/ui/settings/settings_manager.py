from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal

from .app_settings_store import AppSettingsStore
from .display_settings import DisplaySettings
from .recording_settings import RecordingSettings


class SettingsManager(QObject):
    DEFAULT_LABELS = ("dry_swallow", "water_5ml", "cough")
    DEFAULT_RECORDING_DIR_NAME = "data"

    labelsChanged = pyqtSignal(tuple)
    saveDirChanged = pyqtSignal(str)

    def __init__(
        self,
        settings_store: AppSettingsStore,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self.settings_store = settings_store

        self.display_settings = DisplaySettings(
            parent=self,
            **self.settings_store.load_display_settings(),
        )
        self.recording_settings = RecordingSettings(
            parent=self,
            **self.settings_store.load_recording_settings(),
        )

        self._labels = self.settings_store.load_labels(self._default_labels())
        self._default_save_dir = self.settings_store.load_default_save_dir(
            self._default_recording_dir()
        )

        self._connect_persistence()

        self._save_display_settings()
        self._save_recording_settings()
        self._save_labels()
        self._save_default_save_dir()

    @property
    def labels(self) -> tuple[str, ...]:
        return tuple(self._labels)

    @property
    def default_save_dir(self) -> str:
        return self._default_save_dir

    def add_label(self, label: str) -> None:
        normalized = str(label).strip()
        if not normalized or normalized in self._labels:
            return

        self._labels.append(normalized)
        self._save_labels()
        self.labelsChanged.emit(self.labels)

    def remove_label(self, label: str) -> None:
        normalized = str(label).strip()
        if normalized not in self._labels:
            return

        self._labels.remove(normalized)
        self._save_labels()
        self.labelsChanged.emit(self.labels)

    def set_default_save_dir(self, save_dir: str) -> None:
        normalized = str(Path(save_dir).expanduser()).strip()
        if not normalized or normalized == self._default_save_dir:
            return

        self._default_save_dir = normalized
        self._save_default_save_dir()
        self.saveDirChanged.emit(self._default_save_dir)

    def _save_display_settings(self, *_args) -> None:
        self.settings_store.save_display_settings(self.display_settings)

    def _save_recording_settings(self, *_args) -> None:
        self.settings_store.save_recording_settings(self.recording_settings)

    def _save_labels(self) -> None:
        self.settings_store.save_labels(self._labels)

    def _save_default_save_dir(self) -> None:
        self.settings_store.save_default_save_dir(self._default_save_dir)

    def _default_labels(self) -> list[str]:
        return list(self.DEFAULT_LABELS)

    def _default_recording_dir(self) -> str:
        return str((Path.cwd() / self.DEFAULT_RECORDING_DIR_NAME).resolve())

    def _connect_persistence(self) -> None:
        self.display_settings.maxSamplesChanged.connect(self._save_display_settings)
        self.display_settings.channelVisibilityChanged.connect(self._save_display_settings)
        self.display_settings.yAxisAutoChanged.connect(self._save_display_settings)
        self.display_settings.yAxisBoundsChanged.connect(self._save_display_settings)
        self.display_settings.plotHeightChanged.connect(self._save_display_settings)
        self.recording_settings.recordingModeChanged.connect(self._save_recording_settings)
