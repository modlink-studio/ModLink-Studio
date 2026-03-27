from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtProperty

from modlink_core.runtime.engine import ModLinkEngine

from .device_page import DevicePageController
from .main_page import MainPageController
from .settings_page import SettingsPageController


class AppController(QObject):
    def __init__(self, engine: ModLinkEngine, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._main_page = MainPageController(engine, parent=self)
        self._device_page = DevicePageController(engine, parent=self)
        self._settings_page = SettingsPageController(parent=self)

    @pyqtProperty(str, constant=True)
    def applicationTitle(self) -> str:
        return "ModLink Studio QML"

    @pyqtProperty(QObject, constant=True)
    def mainPage(self) -> QObject:
        return self._main_page

    @pyqtProperty(QObject, constant=True)
    def devicePage(self) -> QObject:
        return self._device_page

    @pyqtProperty(QObject, constant=True)
    def settingsPage(self) -> QObject:
        return self._settings_page
