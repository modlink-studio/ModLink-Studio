from __future__ import annotations

from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import QWidget
from qfluentwidgets import FluentIcon as FIF, MSFluentWindow

from packages.modlink_core.runtime.engine import ModLinkEngine

from .pages import MainPage


class MainWindow(MSFluentWindow):
    """Application shell for ModLink Studio."""

    def __init__(self, engine: ModLinkEngine, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.engine = engine

        self.main_page = MainPage(engine=self.engine, parent=self)

        self.addSubInterface(self.main_page, FIF.HOME, "主页")

        self.resize(980, 680)
        self.setMinimumSize(920, 640)
        self.setWindowTitle("ModLink Studio")

        self.navigationInterface.setIndicatorAnimationEnabled(False)
        self.stackedWidget.setAnimationEnabled(False)

    def closeEvent(self, event: QCloseEvent) -> None:
        # Ensure worker threads are stopped before the window is destroyed.
        self.engine.shutdown()
        super().closeEvent(event)
