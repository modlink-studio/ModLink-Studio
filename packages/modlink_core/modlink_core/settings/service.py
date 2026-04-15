from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from .core import SettingsStore


class SettingsService(SettingsStore):
    def __init__(
        self,
        path: str | Path | None = None,
        parent: object | None = None,
        *,
        on_change: Callable[[str, Any], None] | None = None,
    ) -> None:
        del parent
        super().__init__(path=path, on_change=on_change)
