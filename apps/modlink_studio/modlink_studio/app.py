from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QMessageBox

from modlink_core import configure_host_logging

from .debug_bootstrap import install_debug_bootstrap
from .startup import (
    load_app_icon,
    load_runtime_deps,
    set_windows_app_user_model_id,
    show_splash_screen,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _LaunchOptions:
    log_path: Path | None
    qt_args: tuple[str, ...]


def _parse_launch_options(
    argv: Sequence[str] | None = None,
    *,
    prog: str,
) -> _LaunchOptions:
    parser = argparse.ArgumentParser(
        prog=prog,
        description="Start the ModLink Studio desktop host.",
    )
    parser.add_argument(
        "--log-path",
        type=Path,
        help="write the rotating desktop log to a specific file",
    )
    raw_args = list(argv) if argv is not None else list(sys.argv[1:])
    namespace, qt_args = parser.parse_known_args(raw_args)
    return _LaunchOptions(
        log_path=namespace.log_path,
        qt_args=tuple(str(arg) for arg in qt_args),
    )


def _create_application(argv: Sequence[str]) -> QApplication:
    existing = QApplication.instance()
    if existing is not None:
        return existing
    set_windows_app_user_model_id()
    app = QApplication(list(argv))
    app.setApplicationName("ModLink Studio")
    app.setOrganizationName("ModLink")
    app.setWindowIcon(load_app_icon())
    return app


def _shutdown_bridge_with_prompt(bridge: object) -> None:
    try:
        bridge.shutdown()
    except Exception as exc:
        QMessageBox.critical(None, "ModLink Studio", f"关闭后台资源时发生错误。\n\n{exc}")


def _run_app(argv: Sequence[str] | None, *, debug: bool, prog: str) -> None:
    options = _parse_launch_options(argv, prog=prog)
    if debug:
        install_debug_bootstrap()
    log_path = configure_host_logging(
        log_path=options.log_path,
        log_filename="modlink-studio.log",
        debug=debug,
    )
    logger.info("Starting ModLink Studio (logs at %s)", log_path)
    if debug:
        logger.info("Debug mode enabled")

    app = _create_application([prog, *options.qt_args])
    icon = load_app_icon()

    # Splash first, then heavy imports under it. Reordering here trades
    # 1.5 s of cold-start blank screen for a brand splash within ~280 ms,
    # and avoids a first-frame stall when the user opens a signal preview.
    splash = show_splash_screen(icon)
    deps = load_runtime_deps()
    deps.pg.setConfigOptions(useOpenGL=True)
    deps.set_theme(deps.theme_auto)
    if splash is not None:
        QApplication.processEvents()

    runtime = deps.ModLinkEngine(parent=app)
    bridge = deps.QtModLinkBridge(runtime, parent=app)
    app.aboutToQuit.connect(lambda: _shutdown_bridge_with_prompt(bridge))

    window = deps.MainWindow(engine=bridge)
    window.setWindowIcon(icon)
    window.show()
    if splash is not None:
        splash.finish()
    raise SystemExit(app.exec())


def main(argv: Sequence[str] | None = None) -> None:
    """Single supported non-debug startup entry for ModLink Studio."""
    _run_app(argv, debug=False, prog="modlink-studio")


def debug_main(argv: Sequence[str] | None = None) -> None:
    """Console-backed debug startup entry for ModLink Studio."""
    _run_app(argv, debug=True, prog="modlink-studio-debug")
