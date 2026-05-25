from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path

from PyQt6.QtCore import QSize
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import QApplication, QMessageBox

from modlink_core import configure_host_logging

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


_WINDOWS_APP_USER_MODEL_ID = "ModLink.Studio.Desktop"


def _set_windows_app_user_model_id() -> None:
    """Tag the process with our own Windows AppUserModelID.

    Without this call Windows groups the process under the generic
    ``python.exe`` AUMID, and the taskbar / Alt-Tab can pick up a stale
    cached icon (often the default Python snake) on cold start. Setting
    the AUMID before the first ``QApplication`` instance is created lets
    the taskbar bind our packaged icon stably across launches.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            _WINDOWS_APP_USER_MODEL_ID,
        )
    except (AttributeError, OSError):
        # Older Windows shells without the API, or sandboxed contexts that
        # block the call, simply fall back to the default behaviour.
        return


def _create_application(argv: Sequence[str] | None = None) -> QApplication:
    """Create or reuse the process-level Qt application."""

    existing = QApplication.instance()
    if existing is not None:
        return existing

    _set_windows_app_user_model_id()
    app = QApplication(list(argv) if argv is not None else sys.argv)
    app.setApplicationName("ModLink Studio")
    app.setOrganizationName("ModLink")
    app.setWindowIcon(_load_app_icon())
    return app


def _shutdown_bridge_with_prompt(bridge: object) -> None:
    """Drain the Qt bridge cleanly and surface any teardown error.

    The parameter is annotated as ``object`` so we don't have to import
    ``QtModLinkBridge`` at app module load time (that import drags scipy and
    qfluentwidgets in via ``modlink_ui``). The actual type comes from
    ``_run_app`` after the splash screen is already visible.
    """
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
    icon = _load_app_icon()

    # Show the splash screen before any heavy imports / construction so the
    # user sees the app brand within ~100 ms instead of staring at a blank
    # screen for the full ~1.5 s of cold-start work. Heavy modules
    # (modlink_ui, scipy.signal, pyqtgraph theming, the engine bootstrap)
    # are imported eagerly under the splash to keep the runtime hot path
    # free of first-frame stalls.
    splash = _show_startup_splash(icon)

    deps = _load_runtime_deps()
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


@dataclass(frozen=True)
class _RuntimeDeps:
    """Heavy modules loaded after the splash screen is on screen.

    Bundling them through a small helper keeps the runtime startup ordering
    explicit and gives the Studio app smoke test a single seam it can replace
    with stubs, rather than monkey-patching individual module attributes.
    """

    pg: object
    set_theme: object
    theme_auto: object
    ModLinkEngine: object
    QtModLinkBridge: object
    MainWindow: object


def _load_runtime_deps() -> _RuntimeDeps:
    import pyqtgraph as pg
    from qfluentwidgets import Theme, setTheme

    from modlink_core import ModLinkEngine
    from modlink_ui import MainWindow
    from modlink_ui.bridge import QtModLinkBridge

    return _RuntimeDeps(
        pg=pg,
        set_theme=setTheme,
        theme_auto=Theme.AUTO,
        ModLinkEngine=ModLinkEngine,
        QtModLinkBridge=QtModLinkBridge,
        MainWindow=MainWindow,
    )


_SPLASH_WINDOW_SIZE = QSize(420, 280)
_SPLASH_ICON_SIZE = QSize(112, 112)


def _show_startup_splash(icon: QIcon):
    """Show a borderless splash screen carrying our app icon.

    Returns the ``SplashScreen`` instance, or ``None`` when running in a
    context where the splash cannot be created (for example a headless
    smoke test that already replaced ``QApplication`` with a stub). The
    parent is left as ``None`` so the splash works as an early standalone
    window before ``MainWindow`` exists.
    """
    if QApplication.instance() is None:
        return None
    try:
        from qfluentwidgets import SplashScreen
    except ImportError:
        return None

    from PyQt6.QtCore import Qt

    splash = SplashScreen(icon, parent=None)
    splash.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
    splash.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
    splash.setIconSize(_SPLASH_ICON_SIZE)
    splash.resize(_SPLASH_WINDOW_SIZE)

    primary_screen = QApplication.primaryScreen()
    if primary_screen is not None:
        screen_geometry = primary_screen.availableGeometry()
        splash.move(
            screen_geometry.center().x() - splash.width() // 2,
            screen_geometry.center().y() - splash.height() // 2,
        )
    splash.show()
    QApplication.processEvents()
    return splash


def main(argv: Sequence[str] | None = None) -> None:
    """Single supported non-debug startup entry for ModLink Studio."""

    _run_app(argv, debug=False, prog="modlink-studio")


def debug_main(argv: Sequence[str] | None = None) -> None:
    """Console-backed debug startup entry for ModLink Studio."""

    _run_app(argv, debug=True, prog="modlink-studio-debug")
