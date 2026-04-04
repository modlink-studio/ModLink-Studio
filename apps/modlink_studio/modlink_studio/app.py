from __future__ import annotations

import sys
from collections.abc import Sequence
from importlib.resources import files
from pathlib import Path

import pyqtgraph as pg
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import QApplication, QMessageBox
from qfluentwidgets import Theme, setTheme

from modlink_core import ModLinkEngine
from modlink_core.drivers import discover_driver_factories
from modlink_core.settings.service import SettingsService
from modlink_qt_bridge import QtModLinkBridge
from modlink_ui import MainWindow


def _load_app_icon() -> QIcon:
    icon = _load_packaged_app_icon()
    if not icon.isNull():
        return icon

    # Keep a repo-local fallback so editable/dev runs still pick up the asset.
    assets_dir = Path(__file__).resolve().parents[3] / "assets"
    icon_path = assets_dir / "app_icon.png"
    if icon_path.is_file():
        return QIcon(str(icon_path))
    return QIcon()


def _load_packaged_app_icon() -> QIcon:
    try:
        icon_bytes = files("modlink_studio").joinpath("app_icon.png").read_bytes()
    except (FileNotFoundError, ModuleNotFoundError, OSError):
        return QIcon()

    pixmap = QPixmap()
    if not pixmap.loadFromData(icon_bytes):
        return QIcon()

    icon = QIcon()
    icon.addPixmap(pixmap)
    return icon


def _create_application(argv: Sequence[str] | None = None) -> QApplication:
    """Create or reuse the process-level Qt application."""

    existing = QApplication.instance()
    if existing is not None:
        return existing

    app = QApplication(list(argv) if argv is not None else sys.argv)
    app.setApplicationName("ModLink Studio")
    app.setOrganizationName("ModLink")
    app.setWindowIcon(_load_app_icon())
    return app


def _shutdown_bridge_with_prompt(bridge: QtModLinkBridge) -> None:
    try:
        bridge.shutdown()
    except Exception as exc:
        QMessageBox.critical(
            None,
            "ModLink Studio",
            f"关闭后台资源时发生错误。\n\n{exc}",
        )


def main() -> None:
    """Single supported startup entry for ModLink Studio."""

    app = _create_application()
    pg.setConfigOptions(useOpenGL=True)
    setTheme(Theme.AUTO)
    settings = SettingsService(parent=app)
    driver_factories = discover_driver_factories()
    runtime = ModLinkEngine(
        driver_factories=driver_factories,
        settings=settings,
        parent=app,
    )
    bridge = QtModLinkBridge(runtime, parent=app)
    app.aboutToQuit.connect(lambda: _shutdown_bridge_with_prompt(bridge))
    window = MainWindow(engine=bridge)
    window.setWindowIcon(_load_app_icon())
    window.show()
    raise SystemExit(app.exec())
