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
from ..widgets import GanglionConnectionCard, LabelManagerCard, SaveDirectoryCard


class SettingsPage(QWidget):
    def __init__(
        self,
        backend: GanglionBackendBase,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self.setObjectName("settings-page")
        self.backend = backend

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(36, 28, 36, 28)
        root_layout.setSpacing(20)

        header_label = SubtitleLabel("设置", self)
        intro_label = BodyLabel(
            "这个页面用于承接设备参数、主题、数据保存、日志和实验默认值。",
            self,
        )
        intro_label.setWordWrap(True)

        self.scroll_area = SingleDirectionScrollArea(self, orient=Qt.Orientation.Vertical)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setSmoothMode(SmoothMode.NO_SMOOTH)
        self.scroll_area.enableTransparentBackground()

        self.scroll_widget = QWidget(self.scroll_area)
        self.scroll_widget.setObjectName("settings-scroll-widget")
        self.scroll_widget.setStyleSheet("QWidget#settings-scroll-widget { background: transparent; }")

        scroll_layout = QVBoxLayout(self.scroll_widget)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(20)

        connection_group = SettingCardGroup("设备连接", self.scroll_widget)
        connection_group.addSettingCard(GanglionConnectionCard(self.backend, connection_group))

        storage_group = SettingCardGroup("数据保存", self.scroll_widget)
        storage_group.addSettingCard(SaveDirectoryCard(self.backend, storage_group))

        labels_group = SettingCardGroup("标签设置", self.scroll_widget)
        labels_group.addSettingCard(LabelManagerCard(self.backend, labels_group))

        scroll_layout.addWidget(connection_group)
        scroll_layout.addWidget(storage_group)
        scroll_layout.addWidget(labels_group)
        scroll_layout.addStretch(1)

        self.scroll_area.setWidget(self.scroll_widget)

        root_layout.addWidget(header_label)
        root_layout.addWidget(intro_label)
        root_layout.addWidget(self.scroll_area, 1)
