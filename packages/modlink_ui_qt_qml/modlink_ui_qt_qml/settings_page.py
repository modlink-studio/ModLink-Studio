from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

from modlink_core.settings import SettingsGroup, SettingsStr
from modlink_core.storage import STORAGE_ROOT_DIR_KEY, resolved_storage_root_dir
from modlink_qt_bridge import QtModLinkBridge

from .constants import (
    PREVIEW_REFRESH_RATE_OPTIONS,
    UI_LABELS_KEY,
    UI_PREVIEW_REFRESH_RATE_HZ_KEY,
    declare_label_settings,
    declare_preview_refresh_rate_settings,
    normalize_labels,
    normalize_preview_refresh_rate_hz,
    serialize_labels,
)


class SettingsPageController(QObject):
    saveDirectoryChanged = pyqtSignal()
    previewRefreshRateHzChanged = pyqtSignal()
    labelsChanged = pyqtSignal()
    messageRaised = pyqtSignal(str)

    def __init__(
        self,
        engine: QtModLinkBridge,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._settings = engine.settings
        self._settings.add(
            storage=SettingsGroup(
                root_dir=SettingsStr(default=""),
                export_root_dir=SettingsStr(default=""),
            )
        )
        declare_preview_refresh_rate_settings(self._settings)
        declare_label_settings(self._settings)
        if self._settings.path is not None and self._settings.path.exists():
            self._settings.load(ignore_unknown=True)
        self._settings.sig_setting_changed.connect(self._on_setting_changed)

    @pyqtProperty(str, notify=saveDirectoryChanged)
    def saveDirectory(self) -> str:
        return str(resolved_storage_root_dir(self._settings))

    @pyqtProperty(int, notify=previewRefreshRateHzChanged)
    def previewRefreshRateHz(self) -> int:
        return normalize_preview_refresh_rate_hz(self._settings.ui.preview.refresh_rate_hz.value)

    @pyqtProperty("QVariantList", constant=True)
    def previewRateOptions(self) -> list[int]:
        return list(PREVIEW_REFRESH_RATE_OPTIONS)

    @pyqtProperty("QVariantList", notify=labelsChanged)
    def labels(self) -> list[str]:
        return list(normalize_labels(self._settings.ui.labels.items.value))

    @pyqtSlot(str)
    def setSaveDirectory(self, value: str) -> None:
        normalized = str(value).strip()
        if not normalized:
            self.messageRaised.emit("保存目录不能为空。")
            return
        self._settings.storage.root_dir = str(Path(normalized).expanduser())
        self._settings.save()
        self.messageRaised.emit("保存目录已更新。")

    @pyqtSlot(int)
    def setPreviewRefreshRateHz(self, value: int) -> None:
        normalized = normalize_preview_refresh_rate_hz(value)
        self._settings.ui.preview.refresh_rate_hz = normalized
        self._settings.save()
        self.messageRaised.emit(f"预览刷新率已切换到 {normalized} Hz。")

    @pyqtSlot(str)
    def addLabel(self, value: str) -> None:
        text = str(value).strip()
        if not text:
            return
        labels = normalize_labels([*self.labels, text])
        self._settings.ui.labels.items = serialize_labels(labels)
        self._settings.save()
        self.messageRaised.emit(f"已添加标签 {text}。")

    @pyqtSlot(str)
    def removeLabel(self, value: str) -> None:
        text = str(value).strip()
        if not text:
            return
        labels = tuple(label for label in self.labels if label != text)
        normalized = normalize_labels(labels)
        self._settings.ui.labels.items = serialize_labels(normalized)
        self._settings.save()
        self.messageRaised.emit(f"已移除标签 {text}。")

    def _on_setting_changed(self, event: object) -> None:
        key = getattr(event, "key", None)
        if key == STORAGE_ROOT_DIR_KEY:
            self.saveDirectoryChanged.emit()
        elif key == UI_PREVIEW_REFRESH_RATE_HZ_KEY:
            self.previewRefreshRateHzChanged.emit()
        elif key == UI_LABELS_KEY:
            self.labelsChanged.emit()
