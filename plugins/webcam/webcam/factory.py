from __future__ import annotations

from .driver import WebcamDriver


def create_driver() -> WebcamDriver:
    return WebcamDriver()
