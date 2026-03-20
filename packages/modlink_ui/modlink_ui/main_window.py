from __future__ import annotations

from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import QWidget
from qfluentwidgets import FluentIcon as FIF, MSFluentWindow
from qfluentwidgets.components.navigation import NavigationItemPosition

from modlink_core.runtime.engine import ModLinkEngine

from .pages import DevicePage, MainPage, SettingsPage


class MainWindow(MSFluentWindow):
    """Application shell for ModLink Studio."""

    def __init__(self, engine: ModLinkEngine, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.engine = engine

        self.main_page = MainPage(engine=self.engine, parent=self)
        self.device_page = DevicePage(parent=self)
        self.settings_page = SettingsPage(parent=self)

        self.addSubInterface(self.main_page, FIF.HOME, "主页")
        self.addSubInterface(self.device_page, FIF.IOT, "设备", position=NavigationItemPosition.BOTTOM)
        self.addSubInterface(self.settings_page, FIF.SETTING, "设置", position=NavigationItemPosition.BOTTOM)

        self.resize(980, 680)
        self.setMinimumSize(920, 640)
        self.setWindowTitle("ModLink Studio")

        self.navigationInterface.setIndicatorAnimationEnabled(False)
        self.stackedWidget.setAnimationEnabled(False)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.engine.shutdown()
        super().closeEvent(event)
