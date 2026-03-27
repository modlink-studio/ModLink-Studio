from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

from PyQt6.QtCore import QObject
from PyQt6.QtGui import QIcon
from PyQt6.QtQml import QQmlApplicationEngine
from PyQt6.QtWidgets import QApplication

from modlink_core.runtime.engine import ModLinkEngine

from .app_controller import AppController


def _load_app_icon() -> QIcon:
    assets_dir = Path(__file__).resolve().parents[3] / "assets"
    icon_path = assets_dir / "app_icon.png"
    if icon_path.is_file():
        return QIcon(str(icon_path))
    return QIcon()


def create_application(argv: Sequence[str] | None = None) -> QApplication:
    existing = QApplication.instance()
    if existing is not None:
        return existing

    app = QApplication(list(argv) if argv is not None else sys.argv)
    app.setApplicationName("ModLink Studio QML")
    app.setOrganizationName("ModLink")
    app.setWindowIcon(_load_app_icon())
    return app


def load_window(
    engine: ModLinkEngine,
    *,
    parent: QObject | None = None,
) -> tuple[QQmlApplicationEngine, AppController]:
    controller = AppController(engine, parent=parent)
    qml_engine = QQmlApplicationEngine(parent)
    qml_engine.rootContext().setContextProperty("appController", controller)
    main_qml = Path(__file__).resolve().parent / "qml" / "Main.qml"
    qml_engine.load(str(main_qml))
    if not qml_engine.rootObjects():
        raise RuntimeError(f"failed to load QML window: {main_qml}")
    return qml_engine, controller
