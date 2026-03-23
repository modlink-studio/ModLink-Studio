from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget
from qfluentwidgets import ComboBox, FluentIcon as FIF, SettingCard

from modlink_core.settings.service import SettingsService

from ...ui_settings import (
    PREVIEW_REFRESH_RATE_OPTIONS,
    UI_PREVIEW_REFRESH_RATE_HZ_KEY,
    load_preview_refresh_rate_hz,
    save_preview_refresh_rate_hz,
)


class PreviewRefreshRateCard(SettingCard):
    def __init__(self, parent: QWidget | None = None) -> None:
        self._settings = SettingsService.instance()
        self._refresh_rate_hz = load_preview_refresh_rate_hz(self._settings)

        super().__init__(
            FIF.SPEED_HIGH,
            "预览刷新率",
            self._content_text(self._refresh_rate_hz),
            parent,
        )

        self.combo_box = ComboBox(self)
        self.combo_box.setFixedWidth(120)
        for rate_hz in PREVIEW_REFRESH_RATE_OPTIONS:
            self.combo_box.addItem(f"{rate_hz} Hz", userData=rate_hz)

        self.hBoxLayout.addWidget(self.combo_box, 0, Qt.AlignmentFlag.AlignRight)
        self.hBoxLayout.addSpacing(16)

        self.combo_box.currentIndexChanged.connect(self._on_index_changed)
        self._settings.sig_setting_changed.connect(self._on_setting_changed)
        self._refresh_ui()

    def _on_index_changed(self, index: int) -> None:
        rate_hz = self.combo_box.itemData(index)
        self._refresh_rate_hz = save_preview_refresh_rate_hz(rate_hz, self._settings)
        self._refresh_ui()

    def _on_setting_changed(self, event: object) -> None:
        if getattr(event, "key", None) != UI_PREVIEW_REFRESH_RATE_HZ_KEY:
            return
        self._refresh_rate_hz = load_preview_refresh_rate_hz(self._settings)
        self._refresh_ui()

    def _refresh_ui(self) -> None:
        index = self.combo_box.findData(self._refresh_rate_hz)
        if index >= 0 and index != self.combo_box.currentIndex():
            self.combo_box.setCurrentIndex(index)

        self.setContent(self._content_text(self._refresh_rate_hz))

    @staticmethod
    def _content_text(refresh_rate_hz: int) -> str:
        return f"当前 {refresh_rate_hz} Hz。刷新率越高越流畅，也越占用资源。"
