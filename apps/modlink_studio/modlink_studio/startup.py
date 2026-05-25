"""One-shot helpers that run during desktop startup.

These exist as their own module so ``app.py`` can stay focused on the
top-to-bottom launch sequence. Everything here is called once per
process: icon loading, the Windows AUMID tag, the splash screen, and
the deferred heavy import chain that lives behind the splash.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import QApplication

WINDOWS_APP_USER_MODEL_ID = "ModLink.Studio.Desktop"
SPLASH_WINDOW_SIZE = QSize(420, 280)
SPLASH_ICON_SIZE = QSize(112, 112)


def load_app_icon() -> QIcon:
    """Return the packaged ``app_icon.png`` as a :class:`QIcon`.

    Falls back to the repo-local copy under ``assets/`` so editable
    installs without ``setup.py`` package data still find it.
    """
    try:
        icon_bytes = files("modlink_studio").joinpath("app_icon.png").read_bytes()
    except (FileNotFoundError, ModuleNotFoundError, OSError):
        icon_bytes = None

    if icon_bytes is not None:
        pixmap = QPixmap()
        if pixmap.loadFromData(icon_bytes):
            icon = QIcon()
            icon.addPixmap(pixmap)
            return icon

    repo_icon_path = Path(__file__).resolve().parents[3] / "assets" / "app_icon.png"
    if repo_icon_path.is_file():
        return QIcon(str(repo_icon_path))
    return QIcon()


def set_windows_app_user_model_id() -> None:
    """Bind the process to our own AUMID so the Windows taskbar uses our icon
    instead of the cached ``python.exe`` default."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            WINDOWS_APP_USER_MODEL_ID,
        )
    except (AttributeError, OSError):
        return


def show_splash_screen(icon: QIcon):
    """Display a borderless splash with our icon and return the widget.

    Returns ``None`` when no ``QApplication`` exists yet or qfluentwidgets
    is unavailable; callers must tolerate that to keep smoke tests cheap.
    """
    if QApplication.instance() is None:
        return None
    try:
        from qfluentwidgets import SplashScreen
    except ImportError:
        return None

    splash = SplashScreen(icon, parent=None)
    splash.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
    splash.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
    splash.setIconSize(SPLASH_ICON_SIZE)
    splash.resize(SPLASH_WINDOW_SIZE)

    primary_screen = QApplication.primaryScreen()
    if primary_screen is not None:
        center = primary_screen.availableGeometry().center()
        splash.move(center.x() - splash.width() // 2, center.y() - splash.height() // 2)
    splash.show()
    QApplication.processEvents()
    return splash


@dataclass(frozen=True)
class RuntimeDeps:
    """Heavy modules pulled in once the splash is on screen."""

    pg: object
    set_theme: object
    theme_auto: object
    ModLinkEngine: object
    QtModLinkBridge: object
    MainWindow: object


def load_runtime_deps() -> RuntimeDeps:
    """Import the engine, Qt bridge, main window, and supporting libraries.

    Done as a function call (rather than module-level imports) so the
    splash screen can be drawn first; the smoke test monkey-patches this
    seam instead of pulling the real chain in.
    """
    import pyqtgraph as pg
    from qfluentwidgets import Theme, setTheme

    from modlink_core import ModLinkEngine
    from modlink_ui import MainWindow
    from modlink_ui.bridge import QtModLinkBridge

    return RuntimeDeps(
        pg=pg,
        set_theme=setTheme,
        theme_auto=Theme.AUTO,
        ModLinkEngine=ModLinkEngine,
        QtModLinkBridge=QtModLinkBridge,
        MainWindow=MainWindow,
    )
