from __future__ import annotations

from PyQt6.QtWidgets import QWidget


class SettingsPage(QWidget):
    """Empty settings page placeholder."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.setObjectName("settings-page")