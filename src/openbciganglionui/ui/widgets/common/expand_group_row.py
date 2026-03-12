from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QWidget


class ExpandGroupRowContainer(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.row_layout = QHBoxLayout(self)
        self.row_layout.setContentsMargins(48, 14, 48, 14)
        self.row_layout.setSpacing(12)
        self.row_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
