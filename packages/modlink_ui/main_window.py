from __future__ import annotations

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QWidget
from qfluentwidgets import FluentIcon as FIF, FluentWindow

from packages.modlink_core.runtime.engine import ModLinkEngine

from .pages import MainPage


class MainWindow(FluentWindow):
    """Application shell for ModLink Studio."""

    NAV_EXPAND_THRESHOLD = 1100
    NAV_EXPAND_WIDTH = 200

    def __init__(self, engine: ModLinkEngine, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.engine = engine

        self.main_page = MainPage(engine=self.engine, parent=self)

        self.addSubInterface(self.main_page, FIF.HOME, "主页")
        self.navigationInterface.setExpandWidth(self.NAV_EXPAND_WIDTH)
        self.navigationInterface.setMinimumExpandWidth(self.NAV_EXPAND_THRESHOLD)

        self.resize(980, 680)
        self.setMinimumSize(920, 640)
        self.setWindowTitle("ModLink Studio")

        self.navigationInterface.setIndicatorAnimationEnabled(False)
        self.stackedWidget.setAnimationEnabled(False)
        QTimer.singleShot(0, self._sync_navigation_policy)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if not hasattr(self, "navigationInterface"):
            return
        self._sync_navigation_policy()

    def _sync_navigation_policy(self) -> None:
        if not hasattr(self, "navigationInterface"):
            return

        wide_enough = self.width() >= self.NAV_EXPAND_THRESHOLD

        if wide_enough:
            self.navigationInterface.expand(useAni=False)
            self.navigationInterface.setCollapsible(False)
            self.navigationInterface.setMenuButtonVisible(False)
            return

        self.navigationInterface.setMenuButtonVisible(True)
        self.navigationInterface.setCollapsible(True)

        panel = getattr(self.navigationInterface, "panel", None)
        if panel is not None and hasattr(panel, "collapse"):
            panel.collapse()
