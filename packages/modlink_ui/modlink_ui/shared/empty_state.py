from __future__ import annotations

from PyQt6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, StrongBodyLabel


class EmptyStateMessage(QWidget):
    def __init__(self, title: str, body: str, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.setObjectName("empty-state-message")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

        self.title_label = StrongBodyLabel(title, self)
        self.body_label = BodyLabel(body, self)
        self.body_label.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self.title_label)
        layout.addWidget(self.body_label)
