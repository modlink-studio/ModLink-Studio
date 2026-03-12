from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import FlowLayout, LineEdit, PushButton, PushSettingCard
from qfluentwidgets import FluentIcon as FIF

from ...settings import DEFAULT_RADIUS, SMALL_RADIUS, SettingsManager


class CountBadge(QLabel):
    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent=parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumWidth(44)
        self.setStyleSheet(
            f"""
            QLabel {{
                color: rgb(36, 72, 124);
                background: rgba(95, 154, 255, 0.16);
                border: 1px solid rgba(95, 154, 255, 0.28);
                border-radius: {DEFAULT_RADIUS}px;
                padding: 4px 12px;
                font-weight: 600;
            }}
            """
        )


class LabelChip(QFrame):
    def __init__(
        self,
        text: str,
        on_remove,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self.label_text = text
        self.on_remove = on_remove
        self.setObjectName("label-chip")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 5, 8, 5)
        layout.setSpacing(6)

        self.text_label = QLabel(text, self)
        text_font = QFont(self.text_label.font())
        text_font.setPointSize(11)
        text_font.setWeight(QFont.Weight.Medium)
        self.text_label.setFont(text_font)
        self.text_label.setStyleSheet(
            """
            QLabel {
                background: transparent;
                border: none;
                padding: 0;
                color: rgb(32, 32, 32);
            }
            """
        )

        self.remove_button = QToolButton(self)
        self.remove_button.setText("×")
        self.remove_button.setAutoRaise(True)
        self.remove_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.remove_button.setFixedSize(22, 22)
        button_font = QFont(self.remove_button.font())
        button_font.setPointSize(11)
        button_font.setWeight(QFont.Weight.Medium)
        self.remove_button.setFont(button_font)
        self.remove_button.clicked.connect(self._remove)
        self.remove_button.setStyleSheet(
            f"""
            QToolButton {{
                background: transparent;
                border: none;
                border-radius: {SMALL_RADIUS}px;
                color: rgb(84, 84, 84);
                padding: 0;
            }}
            QToolButton:hover {{
                background: rgba(0, 0, 0, 0.07);
            }}
            QToolButton:pressed {{
                background: rgba(0, 0, 0, 0.12);
            }}
            """
        )

        layout.addWidget(self.text_label)
        layout.addWidget(self.remove_button)

        self.setStyleSheet(
            f"""
            QFrame#label-chip {{
                background: rgb(255, 255, 255);
                border: 1px solid rgba(0, 0, 0, 0.08);
                border-radius: {DEFAULT_RADIUS}px;
            }}
            """
        )

    def _remove(self) -> None:
        self.on_remove(self.label_text)


class LabelInputRow(QWidget):
    def __init__(self, on_submit, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.on_submit = on_submit

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self.input = LineEdit(self)
        self.input.setPlaceholderText("输入一个标签，按 Enter 添加")
        self.input.returnPressed.connect(self._submit)
        self.input.setClearButtonEnabled(True)

        self.add_button = PushButton("添加", self)
        self.add_button.clicked.connect(self._submit)

        layout.addWidget(self.input, 1)
        layout.addWidget(self.add_button)

    def _submit(self) -> None:
        text = self.input.text().strip()
        if not text:
            return
        self.on_submit(text)
        self.input.clear()


class LabelCloudRow(QWidget):
    def __init__(
        self,
        on_remove,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self.on_remove = on_remove
        self.empty_label = QLabel("还没有标签，先添加一个。", self)
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("color: rgb(110, 110, 110);")

        self.flow_layout = FlowLayout(self)
        self.flow_layout.setContentsMargins(0, 0, 0, 0)
        self.flow_layout.setHorizontalSpacing(8)
        self.flow_layout.setVerticalSpacing(8)

    def set_labels(self, labels: list[str]) -> None:
        self.flow_layout.takeAllWidgets()
        for label in labels:
            self.flow_layout.addWidget(LabelChip(label, self.on_remove, self))

        self.empty_label.setVisible(not labels)
        self.empty_label.setGeometry(self.rect())

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.empty_label.setGeometry(self.rect())


class LabelManagerDialog(QDialog):
    def __init__(
        self,
        settings_manager: SettingsManager,
        labels: list[str],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self.settings_manager = settings_manager

        self.setWindowTitle("标签管理")
        self.resize(640, 480)
        self.setMinimumSize(520, 380)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(20, 20, 20, 20)
        root_layout.setSpacing(16)

        header_frame = QFrame(self)
        header_frame.setObjectName("label-manager-panel")
        header_frame.setStyleSheet(
            f"""
            QFrame#label-manager-panel {{
                background: rgba(255, 255, 255, 0.94);
                border: 1px solid rgba(0, 0, 0, 0.08);
                border-radius: {DEFAULT_RADIUS}px;
            }}
            """
        )

        header_frame_layout = QVBoxLayout(header_frame)
        header_frame_layout.setContentsMargins(28, 24, 28, 24)
        header_frame_layout.setSpacing(16)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel("标签管理", self)
        title_font = QFont(title_label.font())
        title_font.setPointSize(14)
        title_font.setWeight(QFont.Weight.DemiBold)
        title_label.setFont(title_font)

        self.count_badge = CountBadge(str(len(labels)), self)

        header_layout.addWidget(title_label)
        header_layout.addStretch(1)
        header_layout.addWidget(self.count_badge)

        tip_label = QLabel("按 Enter 或点击添加按钮新增标签，点击标签右侧 × 删除。", self)
        tip_label.setWordWrap(True)
        tip_label.setStyleSheet("color: rgb(96, 96, 96);")

        self.input_row = LabelInputRow(self.settings_manager.add_label, self)

        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet(
            """
            QScrollArea {
                background: transparent;
            }
            """
        )

        self.label_cloud_row = LabelCloudRow(self.settings_manager.remove_label)
        self.label_cloud_row.setObjectName("label-cloud-row")
        self.label_cloud_row.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.MinimumExpanding,
        )
        scroll_area.setWidget(self.label_cloud_row)

        close_button = PushButton("关闭", self)
        close_button.clicked.connect(self.accept)

        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.addStretch(1)
        footer_layout.addWidget(close_button)

        header_frame_layout.addLayout(header_layout)
        header_frame_layout.addWidget(tip_label)
        header_frame_layout.addWidget(self.input_row)

        root_layout.addWidget(header_frame)
        root_layout.addWidget(scroll_area, 1)
        root_layout.addLayout(footer_layout)

        self.set_labels(labels)

    def set_labels(self, labels: list[str]) -> None:
        self.count_badge.setText(str(len(labels)))
        self.label_cloud_row.set_labels(labels)


class LabelManagerCard(PushSettingCard):
    def __init__(
        self,
        settings_manager: SettingsManager,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(
            "打开",
            FIF.TAG,
            "标签管理器",
            "管理采集标签，点击后在弹窗中编辑",
            parent,
        )
        self.settings_manager = settings_manager
        self.labels = list(settings_manager.labels)
        self.dialog: LabelManagerDialog | None = None

        self.clicked.connect(self._open_dialog)
        self.settings_manager.labelsChanged.connect(self._on_labels_changed)

        self._refresh_summary()

    def _refresh_summary(self) -> None:
        count = len(self.labels)
        self.setContent(f"当前 {count} 个标签，点击后在弹窗中编辑")

    def _open_dialog(self) -> None:
        if self.dialog is None:
            self.dialog = LabelManagerDialog(self.settings_manager, self.labels, self.window())
            self.dialog.finished.connect(self._on_dialog_finished)

        self.dialog.set_labels(self.labels)
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()

    def _on_dialog_finished(self, _result: int) -> None:
        self.dialog = None

    def _on_labels_changed(self, labels: tuple[str, ...]) -> None:
        self.labels = list(labels)
        self._refresh_summary()
        if self.dialog is not None:
            self.dialog.set_labels(self.labels)
