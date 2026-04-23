from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path

import pyqtgraph as pg
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import QApplication, QMessageBox
from qfluentwidgets import Theme, setTheme

from modlink_core import ModLinkEngine, configure_host_logging
from modlink_ui import MainWindow
from modlink_ui.bridge import QtModLinkBridge

from .debug_bootstrap import install_debug_bootstrap

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _LaunchOptions:
    log_path: Path | None
    qt_args: tuple[str, ...]


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


def _build_argument_parser(*, prog: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=prog,
        description="Start the ModLink Studio desktop host.",
    )
    parser.add_argument(
        "--log-path",
        type=Path,
        help="write the rotating desktop log to a specific file",
    )
    return parser


def _parse_launch_options(
    argv: Sequence[str] | None = None,
    *,
    prog: str,
) -> _LaunchOptions:
    parser = _build_argument_parser(prog=prog)
    raw_args = list(argv) if argv is not None else list(sys.argv[1:])
    namespace, qt_args = parser.parse_known_args(raw_args)
    return _LaunchOptions(
        log_path=namespace.log_path,
        qt_args=tuple(str(arg) for arg in qt_args),
    )


def _run_app(
    argv: Sequence[str] | None = None,
    *,
    debug: bool,
    prog: str,
) -> None:
    launch_options = _parse_launch_options(argv, prog=prog)
    if debug:
        install_debug_bootstrap()
    log_path = configure_host_logging(
        log_path=launch_options.log_path,
        log_filename="modlink-studio.log",
        debug=debug,
    )
    logger.info("Starting ModLink Studio")
    logger.info("Desktop logs will be written to %s", log_path)
    if debug:
        logger.info("Debug mode enabled")
    if launch_options.qt_args:
        logger.debug("Forwarding Qt arguments: %s", launch_options.qt_args)

    app = _create_application([prog, *launch_options.qt_args])
    pg.setConfigOptions(useOpenGL=True)
    setTheme(Theme.AUTO)
    runtime = ModLinkEngine(
        parent=app,
    )
    bridge = QtModLinkBridge(runtime, parent=app)
    app.aboutToQuit.connect(lambda: _shutdown_bridge_with_prompt(bridge))
    window = MainWindow(engine=bridge)
    window.setWindowIcon(_load_app_icon())
    window.show()
    raise SystemExit(app.exec())


def main(argv: Sequence[str] | None = None) -> None:
    """Single supported non-debug startup entry for ModLink Studio."""

    _run_app(argv, debug=False, prog="modlink-studio")


def debug_main(argv: Sequence[str] | None = None) -> None:
    """Console-backed debug startup entry for ModLink Studio."""

    _run_app(argv, debug=True, prog="modlink-studio-debug")
