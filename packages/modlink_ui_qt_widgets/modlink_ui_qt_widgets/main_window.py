from __future__ import annotations

import ctypes
import sys

from PyQt6.QtGui import QShowEvent
from PyQt6.QtWidgets import QWidget
from qfluentwidgets import FluentIcon as FIF
from qfluentwidgets import MSFluentWindow
from qfluentwidgets.components.navigation import NavigationItemPosition

from modlink_qt_bridge import QtModLinkBridge

from .pages import DevicePage, MainPage, SettingsPage


class MainWindow(MSFluentWindow):
    """Application shell for ModLink Studio."""

    def __init__(self, engine: QtModLinkBridge, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.engine = engine

        # Keep window composition stable when chart views use OpenGL viewport.
        if hasattr(self, "setMicaEffectEnabled"):
            self.setMicaEffectEnabled(False)

        self.main_page = MainPage(engine=self.engine, parent=self)
        self.device_page = DevicePage(engine=self.engine, parent=self)
        self.settings_page = SettingsPage(engine=self.engine, parent=self)

        self.addSubInterface(self.main_page, FIF.HOME, "实时展示", isTransparent=False)
        self.addSubInterface(
            self.device_page,
            FIF.IOT,
            "设备",
            position=NavigationItemPosition.BOTTOM,
            isTransparent=False,
        )
        self.addSubInterface(
            self.settings_page,
            FIF.SETTING,
            "设置",
            position=NavigationItemPosition.BOTTOM,
            isTransparent=False,
        )

        self.resize(980, 680)
        self.setMinimumSize(920, 640)
        self.setWindowTitle("ModLink Studio")

        self.navigationInterface.setIndicatorAnimationEnabled(False)
        if hasattr(self.navigationInterface, "setAcrylicEnabled"):
            self.navigationInterface.setAcrylicEnabled(False)
        self.stackedWidget.setAnimationEnabled(False)

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self._apply_windows_round_corner_preference()

    def _apply_windows_round_corner_preference(self) -> None:
        if sys.platform != "win32":
            return

        try:
            hwnd = int(self.winId())
            # Win11 DWM attribute values.
            DWMWA_WINDOW_CORNER_PREFERENCE = 33
            DWMWCP_ROUND = 2
            corner_preference = ctypes.c_int(DWMWCP_ROUND)

            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                ctypes.c_void_p(hwnd),
                ctypes.c_uint(DWMWA_WINDOW_CORNER_PREFERENCE),
                ctypes.byref(corner_preference),
                ctypes.sizeof(corner_preference),
            )
        except Exception:
            # Best-effort only; unsupported OS/builds should continue normally.
            return
