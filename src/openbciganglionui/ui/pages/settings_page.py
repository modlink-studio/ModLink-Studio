from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    SettingCardGroup,
    SingleDirectionScrollArea,
    SmoothMode,
    SubtitleLabel,
)

from ...backend import GanglionBackendBase
from ...session import SessionController
from ..settings import SettingsManager
from ..widgets import (
    ChannelBandFilterSettingCard,
    ChannelPowerlineFilterSettingCard,
    ChannelVisibilitySettingCard,
    FilterOrderSettingCard,
    FilterFamilySettingCard,
    FilterScopeSettingCard,
    GanglionConnectionCard,
    LabelManagerCard,
    PointCountSettingCard,
    RecordingModeSettingCard,
    SaveDirectoryCard,
    YAxisRangeSettingCard,
)


class SettingsPage(QWidget):
    def __init__(
        self,
        backend: GanglionBackendBase,
        session_controller: SessionController,
        settings_manager: SettingsManager,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self.setObjectName("settings-page")
        self.backend = backend
        self.session_controller = session_controller
        self.settings_manager = settings_manager

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(36, 28, 36, 28)
        root_layout.setSpacing(20)

        header_label = SubtitleLabel("设置", self)
        intro_label = BodyLabel(
            "这个页面用于配置设备连接、数据保存、录制模式、实时显示、滤波和标签管理。",
            self,
        )
        intro_label.setWordWrap(True)

        self.scroll_area = SingleDirectionScrollArea(
            self, orient=Qt.Orientation.Vertical
        )
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.scroll_area.setSmoothMode(SmoothMode.NO_SMOOTH)
        self.scroll_area.enableTransparentBackground()

        self.scroll_widget = QWidget(self.scroll_area)
        self.scroll_widget.setObjectName("settings-scroll-widget")
        self.scroll_widget.setStyleSheet(
            "QWidget#settings-scroll-widget { background: transparent; }"
        )

        scroll_layout = QVBoxLayout(self.scroll_widget)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(20)
        display_settings = self.settings_manager.display_settings
        recording_settings = self.settings_manager.recording_settings

        connection_group = SettingCardGroup("设备连接", self.scroll_widget)
        connection_group.addSettingCard(
            GanglionConnectionCard(self.backend, connection_group)
        )

        storage_group = SettingCardGroup("数据保存", self.scroll_widget)
        storage_group.addSettingCard(
            SaveDirectoryCard(self.settings_manager, storage_group)
        )

        recording_group = SettingCardGroup("录制设置", self.scroll_widget)
        recording_group.addSettingCard(
            RecordingModeSettingCard(
                recording_settings,
                self.session_controller,
                recording_group,
            )
        )

        display_group = SettingCardGroup("实时显示", self.scroll_widget)
        display_group.cardLayout.setSpacing(8)
        display_group.addSettingCard(
            PointCountSettingCard(display_settings, display_group)
        )
        display_group.addSettingCard(
            ChannelVisibilitySettingCard(display_settings, display_group)
        )
        display_group.addSettingCard(
            YAxisRangeSettingCard(display_settings, display_group)
        )

        filter_group = SettingCardGroup("滤波设置", self.scroll_widget)
        filter_group.cardLayout.setSpacing(8)
        filter_group.addSettingCard(
            FilterScopeSettingCard(display_settings, filter_group)
        )
        filter_group.addSettingCard(
            FilterFamilySettingCard(display_settings, filter_group)
        )
        filter_group.addSettingCard(
            FilterOrderSettingCard(display_settings, filter_group)
        )
        filter_group.addSettingCard(
            ChannelBandFilterSettingCard(display_settings, filter_group)
        )
        filter_group.addSettingCard(
            ChannelPowerlineFilterSettingCard(display_settings, filter_group)
        )

        labels_group = SettingCardGroup("标签设置", self.scroll_widget)
        labels_group.addSettingCard(
            LabelManagerCard(self.settings_manager, labels_group)
        )

        scroll_layout.addWidget(connection_group)
        scroll_layout.addWidget(storage_group)
        scroll_layout.addWidget(recording_group)
        scroll_layout.addWidget(display_group)
        scroll_layout.addWidget(filter_group)
        scroll_layout.addWidget(labels_group)
        scroll_layout.addStretch(1)

        self.scroll_area.setWidget(self.scroll_widget)

        root_layout.addWidget(header_label)
        root_layout.addWidget(intro_label)
        root_layout.addWidget(self.scroll_area, 1)
