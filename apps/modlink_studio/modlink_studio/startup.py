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
from PyQt6.QtWidgets import QApplication

WINDOWS_APP_USER_MODEL_ID = "ModLink.Studio.Desktop"
SPLASH_WINDOW_SIZE = QSize(420, 280)
SPLASH_ICON_SIZE = QSize(112, 112)
SPLASH_STATUS_TEXT = "正在启动 ModLink Studio..."


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
    """Display a borderless splash with our icon, a top-left version badge,
    a status line, and an indeterminate progress bar at the bottom edge."""
    from qfluentwidgets import BodyLabel, IndeterminateProgressBar, SplashScreen, Theme, setTheme

    from . import __version__

    # Apply theme on the main thread before any styled widget is created.
    # qfluentwidgets installs an application-wide event filter that polishes
    # styled widgets on the GUI thread; doing setTheme off-thread races with
    # widget construction and can wipe inline stylesheets.
    setTheme(Theme.AUTO)

    splash = SplashScreen(icon, parent=None)
    splash.setWindowFlags(Qt.WindowType.SplashScreen | Qt.WindowType.WindowStaysOnTopHint)
    splash.titleBar.maxBtn.hide()
    splash.titleBar.closeBtn.clicked.connect(lambda: sys.exit(0))
    splash.setIconSize(SPLASH_ICON_SIZE)
    splash.resize(SPLASH_WINDOW_SIZE)

    width = splash.width()
    height = splash.height()
    side_margin = 12

    # Top-left version badge, mimicking the "Office 2021" pill in Word splash.
    badge = BodyLabel(f"ModLink Studio {__version__}", splash)
    badge.setStyleSheet(
        "QLabel {"
        " background-color: rgba(0, 120, 212, 0.12);"
        " color: rgb(0, 90, 158);"
        " border-radius: 6px;"
        " padding: 4px 10px;"
        " font-weight: 600;"
        "}"
    )
    badge.adjustSize()
    badge.move(side_margin, side_margin)

    # Status line just above the bottom progress bar.
    status_label = BodyLabel(SPLASH_STATUS_TEXT, splash)
    status_label.adjustSize()
    progress_bar = IndeterminateProgressBar(splash)
    progress_bar.setFixedHeight(4)
    progress_bar.setGeometry(0, height - 4, width, 4)
    progress_bar.start()
    status_label.move(side_margin, height - 4 - status_label.height() - 12)

    splash._badge = badge  # keep references alive
    splash._status_label = status_label
    splash._progress_bar = progress_bar

    center = QApplication.primaryScreen().availableGeometry().center()
    splash.move(center.x() - splash.width() // 2, center.y() - splash.height() // 2)
    splash.show()
    _apply_windows_round_corner_preference(splash)
    QApplication.processEvents()
    return splash


def _apply_windows_round_corner_preference(widget) -> None:
    """Ask DWM to round the splash corners on Windows 11, matching the main
    window. Older Windows builds and non-Windows platforms silently fall
    back to square corners."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        DWMWA_WINDOW_CORNER_PREFERENCE = 33
        DWMWCP_ROUND = 2
        preference = ctypes.c_int(DWMWCP_ROUND)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            ctypes.c_void_p(int(widget.winId())),
            ctypes.c_uint(DWMWA_WINDOW_CORNER_PREFERENCE),
            ctypes.byref(preference),
            ctypes.sizeof(preference),
        )
    except Exception:
        return


def load_runtime_deps() -> tuple[type, type, type]:
    """Pull in engine, Qt bridge, main window, plus Qt-wide config knobs.

    Imports happen in a background thread so the splash screen animation
    stays alive. The main thread pumps Qt events at ~60 fps while waiting.
    """
    result: list[object] = []

    def _import_worker() -> None:
        import pyqtgraph as pg

        from modlink_core import ModLinkEngine
        from modlink_ui import MainWindow
        from modlink_ui.bridge import QtModLinkBridge

        pg.setConfigOptions(useOpenGL=True)
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
