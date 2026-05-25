"""One-shot helpers that run during desktop startup.

These exist as their own module so ``app.py`` can stay focused on the
top-to-bottom launch sequence. Everything here is called once per
process: icon loading, the Windows AUMID tag, the splash screen, and
the deferred heavy import chain that lives behind the splash.
"""

from __future__ import annotations

import sys
import time
from importlib.resources import files
from pathlib import Path
from threading import Thread

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import QApplication, QVBoxLayout

WINDOWS_APP_USER_MODEL_ID = "ModLink.Studio.Desktop"
SPLASH_WINDOW_SIZE = QSize(420, 320)
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
    import ctypes

    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(WINDOWS_APP_USER_MODEL_ID)


def show_splash_screen(icon: QIcon):
    """Display a borderless splash with our icon and a loading bar."""
    from qfluentwidgets import IndeterminateProgressBar, SplashScreen

    splash = SplashScreen(icon, parent=None)
    splash.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
    splash.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
    splash.setIconSize(SPLASH_ICON_SIZE)
    splash.resize(SPLASH_WINDOW_SIZE)

    # Add an indeterminate progress bar at the bottom of the splash.
    progress_bar = IndeterminateProgressBar(splash)
    progress_bar.setFixedHeight(4)
    progress_bar.start()

    # Position the bar at the bottom edge.
    layout = QVBoxLayout()
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addStretch(1)
    layout.addWidget(progress_bar)
    # SplashScreen already has a layout for its icon; we overlay ours.
    container = splash
    if container.layout() is None:
        container.setLayout(layout)
    else:
        # Wrap in a child widget that sits at the bottom.
        from PyQt6.QtWidgets import QWidget

        overlay = QWidget(splash)
        overlay.setLayout(layout)
        overlay.setGeometry(0, 0, splash.width(), splash.height())
        overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        overlay.show()
        splash._progress_overlay = overlay  # prevent GC

    center = QApplication.primaryScreen().availableGeometry().center()
    splash.move(center.x() - splash.width() // 2, center.y() - splash.height() // 2)
    splash.show()
    QApplication.processEvents()
    return splash


def load_runtime_deps() -> tuple[type, type, type]:
    """Pull in engine, Qt bridge, main window, plus Qt-wide config knobs.

    Imports happen in a background thread so the splash screen animation
    stays alive. The main thread pumps Qt events at ~60 fps while waiting.
    """
    result: list[object] = []

    def _import_worker() -> None:
        import pyqtgraph as pg
        from qfluentwidgets import Theme, setTheme

        from modlink_core import ModLinkEngine
        from modlink_ui import MainWindow
        from modlink_ui.bridge import QtModLinkBridge

        pg.setConfigOptions(useOpenGL=True)
        setTheme(Theme.AUTO)
        result.extend([ModLinkEngine, QtModLinkBridge, MainWindow])

    thread = Thread(target=_import_worker, name="modlink.startup_import", daemon=True)
    thread.start()
    while thread.is_alive():
        QApplication.processEvents()
        time.sleep(0.016)
    thread.join()

    if len(result) != 3:
        raise RuntimeError("startup import failed")
    return result[0], result[1], result[2]
