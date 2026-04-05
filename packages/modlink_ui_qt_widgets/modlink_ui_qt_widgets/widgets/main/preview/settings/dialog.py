from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QWidget
from qfluentwidgets import (
    CaptionLabel,
    SingleDirectionScrollArea,
    SmoothMode,
    StrongBodyLabel,
)

from modlink_sdk import StreamDescriptor

from .sections import StreamPreviewInfoPanel


class StreamPreviewSettingsPanel(SingleDirectionScrollArea):
    def __init__(
        self,
        descriptor: StreamDescriptor,
        payload_section: QWidget,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent, orient=Qt.Orientation.Vertical)
        self.descriptor = descriptor
        self.payload_section = payload_section

        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setSmoothMode(SmoothMode.LINEAR)
        self.smoothScroll.setDynamicEngineEnabled(True)
        self.smoothScroll.widthThreshold = 0
        self.enableTransparentBackground()

        self.scroll_widget = QWidget(self)
        self.setWidget(self.scroll_widget)

        self.title_label = StrongBodyLabel("预览设置", self.scroll_widget)
        self.tip_label = CaptionLabel(
            "这是模态窗口，关闭前无法操作其他界面。设置会立即生效。",
            self.scroll_widget,
        )
        self.tip_label.setWordWrap(True)

        self.info_panel = StreamPreviewInfoPanel(descriptor, self.scroll_widget)

        layout = QVBoxLayout(self.scroll_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)
        layout.addWidget(self.title_label)
        layout.addWidget(self.tip_label)
        layout.addWidget(self.info_panel)
        layout.addWidget(self.payload_section)
        layout.addStretch(1)


class StreamPreviewSettingsDialog(QDialog):
    def __init__(
        self,
        descriptor: StreamDescriptor,
        payload_section: QWidget,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)
        title = descriptor.display_name or descriptor.stream_id
        self.setWindowTitle(f"{title} · 预览设置")
        self.setModal(True)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.resize(560, 420)
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.content = StreamPreviewSettingsPanel(descriptor, payload_section, self)
        layout.addWidget(self.content)
