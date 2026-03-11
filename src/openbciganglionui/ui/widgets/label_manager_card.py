from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QToolButton, QVBoxLayout, QWidget
from qfluentwidgets import (
    SimpleExpandGroupSettingCard,
    FlowLayout,
    FluentIcon as FIF,
    LineEdit,
)

from ...backend import GanglionBackendBase, LabelsEvent


class CountBadge(QLabel):
    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent=parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumWidth(44)
        self.setStyleSheet(
            """
            QLabel {
                color: rgb(36, 72, 124);
                background: rgba(95, 154, 255, 0.16);
                border: 1px solid rgba(95, 154, 255, 0.28);
                border-radius: 12px;
                padding: 4px 12px;
                font-weight: 600;
            }
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
            """
            QToolButton {
                background: transparent;
                border: none;
                border-radius: 11px;
                color: rgb(84, 84, 84);
                padding: 0;
            }
            QToolButton:hover {
                background: rgba(0, 0, 0, 0.07);
            }
            QToolButton:pressed {
                background: rgba(0, 0, 0, 0.12);
            }
            """
        )

        layout.addWidget(self.text_label)
        layout.addWidget(self.remove_button)

        self.setStyleSheet(
            """
            QFrame#label-chip {
                background: rgba(0, 0, 0, 0.045);
                border: 1px solid rgba(0, 0, 0, 0.08);
                border-radius: 15px;
            }
            """
        )

    def _remove(self) -> None:
        self.on_remove(self.label_text)


class LabelInputRow(QWidget):
    def __init__(self, on_submit, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.on_submit = on_submit

        layout = QVBoxLayout(self)
        layout.setContentsMargins(48, 16, 48, 12)
        layout.setSpacing(0)

        self.input = LineEdit(self)
        self.input.setPlaceholderText("输入一个标签，按 Enter 添加")
        self.input.returnPressed.connect(self._submit)
        self.input.setClearButtonEnabled(True)
        layout.addWidget(self.input)

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

        self.flow_layout = FlowLayout(self)
        self.flow_layout.setContentsMargins(48, 12, 48, 16)
        self.flow_layout.setHorizontalSpacing(8)
        self.flow_layout.setVerticalSpacing(8)

    def set_labels(self, labels: list[str]) -> None:
        self.flow_layout.takeAllWidgets()
        for label in labels:
            self.flow_layout.addWidget(LabelChip(label, self.on_remove, self))


class LabelManagerCard(SimpleExpandGroupSettingCard):
    def __init__(self, backend: GanglionBackendBase, parent: QWidget | None = None) -> None:
        super().__init__(
            FIF.TAG,
            "标签管理器",
            "管理采集标签，按 Enter 快速新增",
            parent,
        )
        self.backend = backend
        self.labels = list(backend.labels)

        self.count_badge = CountBadge("0", self.card)
        self.addWidget(self.count_badge)

        self.input_row = LabelInputRow(self.backend.add_label, self.view)
        self.label_cloud_row = LabelCloudRow(
            self.backend.remove_label,
            self.view,
        )
        self.addGroupWidget(self.input_row)
        self.addGroupWidget(self.label_cloud_row)

        self.backend.sig_labels.connect(self._on_labels_changed)
        self._refresh_groups()
        self.backend.load_labels()

    def _refresh_groups(self) -> None:
        self.count_badge.setText(str(len(self.labels)))
        self.label_cloud_row.set_labels(self.labels)

    def _on_labels_changed(self, event: LabelsEvent) -> None:
        self.labels = list(event.labels)
        self._refresh_groups()
