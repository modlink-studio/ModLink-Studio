from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

from modlink_core.recording.backend import STORAGE_ROOT_DIR_KEY
from modlink_qt_bridge import QtModLinkBridge

from .constants import (
    DEFAULT_LABELS,
    DEFAULT_PREVIEW_REFRESH_RATE_HZ,
    PREVIEW_REFRESH_RATE_OPTIONS,
    UI_LABELS_KEY,
    UI_PREVIEW_REFRESH_RATE_HZ_KEY,
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
        self._settings.sig_setting_changed.connect(self._on_setting_changed)

    @pyqtProperty(str, notify=saveDirectoryChanged)
    def saveDirectory(self) -> str:
        current = self._settings.get(STORAGE_ROOT_DIR_KEY)
        return str(current or "")

    @pyqtProperty(int, notify=previewRefreshRateHzChanged)
    def previewRefreshRateHz(self) -> int:
        return normalize_preview_refresh_rate_hz(
            self._settings.get(
                UI_PREVIEW_REFRESH_RATE_HZ_KEY,
                DEFAULT_PREVIEW_REFRESH_RATE_HZ,
            )
        )

    @pyqtProperty("QVariantList", constant=True)
    def previewRateOptions(self) -> list[int]:
        return list(PREVIEW_REFRESH_RATE_OPTIONS)

    @pyqtProperty("QVariantList", notify=labelsChanged)
    def labels(self) -> list[str]:
        return list(normalize_labels(self._settings.get(UI_LABELS_KEY, DEFAULT_LABELS)))

    @pyqtSlot(str)
    def setSaveDirectory(self, value: str) -> None:
        normalized = str(value).strip()
        if not normalized:
            self.messageRaised.emit("保存目录不能为空。")
            return
        self._settings.set(STORAGE_ROOT_DIR_KEY, normalized)
        self.messageRaised.emit("保存目录已更新。")

    @pyqtSlot(int)
    def setPreviewRefreshRateHz(self, value: int) -> None:
        normalized = normalize_preview_refresh_rate_hz(value)
        self._settings.set(UI_PREVIEW_REFRESH_RATE_HZ_KEY, normalized)
        self.messageRaised.emit(f"预览刷新率已切换到 {normalized} Hz。")

    @pyqtSlot(str)
    def addLabel(self, value: str) -> None:
        text = str(value).strip()
        if not text:
            return
        labels = normalize_labels([*self.labels, text])
        self._settings.set(UI_LABELS_KEY, serialize_labels(labels))
        self.messageRaised.emit(f"已添加标签 {text}。")

    @pyqtSlot(str)
    def removeLabel(self, value: str) -> None:
        text = str(value).strip()
        if not text:
            return
        labels = tuple(label for label in self.labels if label != text)
        normalized = normalize_labels(labels)
        self._settings.set(UI_LABELS_KEY, serialize_labels(normalized))
        self.messageRaised.emit(f"已移除标签 {text}。")

    def _on_setting_changed(self, event: object) -> None:
        key = getattr(event, "key", None)
        if key == STORAGE_ROOT_DIR_KEY:
            self.saveDirectoryChanged.emit()
        elif key == UI_PREVIEW_REFRESH_RATE_HZ_KEY:
            self.previewRefreshRateHzChanged.emit()
        elif key == UI_LABELS_KEY:
            self.labelsChanged.emit()
