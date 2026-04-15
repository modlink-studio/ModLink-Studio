from __future__ import annotations

from PyQt6.QtWidgets import QWidget
from qfluentwidgets import SettingCardGroup

from modlink_qt_bridge import QtModLinkBridge
from modlink_ui_qt_widgets.widgets.settings.cards import (
    LabelManagerCard,
    PreviewRefreshRateCard,
    SaveDirectoryCard,
)
from modlink_ui_qt_widgets.widgets.shared import BasePage


class SettingsPage(BasePage):
    """Settings page for non-device, non-display preferences."""

    def __init__(
        self,
        engine: QtModLinkBridge,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(
            page_key="settings-page",
            title="设置",
            description="配置数据保存、预览刷新率和标签管理。",
            parent=parent,
        )
        self.engine = engine

        storage_group = SettingCardGroup("数据保存", self.scroll_widget)
        storage_group.addSettingCard(
            SaveDirectoryCard(
                self.engine.settings,
                storage_group,
            )
        )

        preview_group = SettingCardGroup("实时展示", self.scroll_widget)
        preview_group.addSettingCard(PreviewRefreshRateCard(self.engine.settings, preview_group))

        labels_group = SettingCardGroup("标签管理", self.scroll_widget)
        labels_group.addSettingCard(LabelManagerCard(self.engine.settings, labels_group))

        self.content_layout.addWidget(storage_group)
        self.content_layout.addWidget(preview_group)
        self.content_layout.addWidget(labels_group)
        self.content_layout.addStretch(1)
