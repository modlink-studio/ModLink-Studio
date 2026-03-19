from __future__ import annotations

import sys
from collections.abc import Sequence

from PyQt6.QtCore import QCoreApplication

from packages.modlink_core import ModLinkRuntime
from packages.modlink_drivers import create_mock_driver_portal


def _create_application(argv: Sequence[str] | None = None) -> QCoreApplication:
    """Create or reuse the process-level Qt application."""

    existing = QCoreApplication.instance()
    if existing is not None:
        return existing

    app = QCoreApplication(list(argv) if argv is not None else sys.argv)
    app.setApplicationName("ModLink Studio")
    app.setOrganizationName("ModLink")
    return app


def _build_runtime(app: QCoreApplication) -> ModLinkRuntime:
    """Compose the current application runtime and its default portals."""

    runtime = ModLinkRuntime(parent=app)
    runtime.attach_portal(
        create_mock_driver_portal(runtime.bus),
        auto_start=True,
    )
    return runtime


def main() -> None:
    """Single supported startup entry for ModLink Studio."""

    app = _create_application()
    runtime = _build_runtime(app)
    print(
        "ModLink Studio runtime initialized",
        f"(portals={len(runtime.driver_portals())}, streams={len(runtime.bus.descriptors())})",
    )
    raise SystemExit(app.exec())
