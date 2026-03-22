from __future__ import annotations

from .driver import OpenBCIGanglionDriver


def create_driver() -> OpenBCIGanglionDriver:
    """Factory used by the ``modlink.drivers`` entry point."""

    return OpenBCIGanglionDriver()
