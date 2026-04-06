from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    SingleDirectionScrollArea,
    SmoothMode,
    SubtitleLabel,
)


class BasePage(QWidget):
    """Shared page shell with a header and adaptive smooth scrolling body."""

    def __init__(
        self,
        *,
        page_key: str,
        title: str,
        description: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self.setObjectName(page_key)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(28, 22, 28, 18)
        root_layout.setSpacing(10)

        self.title_label = SubtitleLabel(title, self)
        self.description_label = BodyLabel(description, self)
        self.description_label.setWordWrap(True)

        self.header_layout = QHBoxLayout()
        self.header_layout.setContentsMargins(0, 0, 0, 0)
        self.header_layout.setSpacing(12)

        self.header_text_layout = QVBoxLayout()
        self.header_text_layout.setContentsMargins(0, 0, 0, 0)
        self.header_text_layout.setSpacing(10)
        self.header_text_layout.addWidget(self.title_label)
        self.header_text_layout.addWidget(self.description_label)

        self.header_action_layout = QHBoxLayout()
        self.header_action_layout.setContentsMargins(0, 0, 0, 0)
        self.header_action_layout.setSpacing(6)
        self.header_action_layout.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight
        )

        self.header_layout.addLayout(self.header_text_layout, 1)
        self.header_layout.addLayout(self.header_action_layout)

        self.scroll_area = SingleDirectionScrollArea(self, orient=Qt.Orientation.Vertical)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setSmoothMode(SmoothMode.LINEAR)

        # Force the time-driven adaptive engine instead of fixed-step scrolling.
        self.scroll_area.smoothScroll.setDynamicEngineEnabled(True)
        self.scroll_area.smoothScroll.widthThreshold = 0

        self.scroll_widget = QWidget(self.scroll_area)
        self.scroll_widget.setObjectName(f"{page_key}-scroll-widget")

        self.content_layout = QVBoxLayout(self.scroll_widget)
        self.content_layout.setContentsMargins(0, 10, 0, 12)
        self.content_layout.setSpacing(20)

        self.scroll_area.setWidget(self.scroll_widget)
        viewport_name = f"{self.scroll_widget.objectName()}-viewport"
        self.scroll_area.viewport().setObjectName(viewport_name)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.scroll_area.viewport().setStyleSheet(
            f"QWidget#{viewport_name} {{ background: transparent; }}"
        )
        self.scroll_widget.setStyleSheet(
            f"QWidget#{self.scroll_widget.objectName()} {{ background: transparent; }}"
        )

        root_layout.addLayout(self.header_layout)
        root_layout.addWidget(self.scroll_area, 1)
