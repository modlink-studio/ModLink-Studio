from PyQt6.QtWidgets import QFrame, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, SubtitleLabel

from ...style_constants import DEFAULT_RADIUS


class PanelWidget(QFrame):
    def __init__(self, title: str, description: str, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.setObjectName(title.replace(" ", "-").lower())

        self.content_layout = QVBoxLayout(self)
        self.content_layout.setContentsMargins(20, 20, 20, 20)
        self.content_layout.setSpacing(8)

        title_label = SubtitleLabel(title, self)
        self.description_label = BodyLabel(description, self)
        self.description_label.setWordWrap(True)

        self.content_layout.addWidget(title_label)
        self.content_layout.addWidget(self.description_label)
        self.content_layout.addStretch(1)

        self.setStyleSheet(
            f"""
            QFrame {{
                background: rgba(255, 255, 255, 0.72);
                border: 1px solid rgba(0, 0, 0, 0.08);
                border-radius: {DEFAULT_RADIUS}px;
            }}
            """
        )

    def set_description(self, description: str) -> None:
        self.description_label.setText(description)
