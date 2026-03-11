from PyQt6.QtWidgets import QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, SettingCardGroup, SubtitleLabel

from ...backend import GanglionBackendBase
from ..widgets import GanglionConnectionCard, LabelManagerCard


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

        root_layout.addWidget(header_label)
        root_layout.addWidget(intro_label)

        connection_group = SettingCardGroup("设备连接", self)
        connection_group.addSettingCard(GanglionConnectionCard(self.backend, connection_group))

        labels_group = SettingCardGroup("标签设置", self)
        labels_group.addSettingCard(LabelManagerCard(self.backend, labels_group))

        root_layout.addWidget(connection_group)
        root_layout.addWidget(labels_group)
        root_layout.addStretch(1)
