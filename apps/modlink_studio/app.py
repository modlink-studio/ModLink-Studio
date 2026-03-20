from __future__ import annotations

import sys
from collections.abc import Sequence

from PyQt6.QtCore import QCoreApplication

from packages.modlink_core import ModLinkEngine
from packages.modlink_core.settings.service import SettingsService
from packages.modlink_drivers import discover_driver_factories


def _create_application(argv: Sequence[str] | None = None) -> QCoreApplication:
    """Create or reuse the process-level Qt application."""

    existing = QCoreApplication.instance()
    if existing is not None:
        return existing

    app = QCoreApplication(list(argv) if argv is not None else sys.argv)
    app.setApplicationName("ModLink Studio")
    app.setOrganizationName("ModLink")
    return app


def main() -> None:
    """Single supported startup entry for ModLink Studio."""

    app = _create_application()
    SettingsService(parent=app)
    driver_factories = discover_driver_factories()
    engine = ModLinkEngine(driver_factories=driver_factories, parent=app)
    print("ModLink Studio engine initialized")
    raise SystemExit(app.exec())
