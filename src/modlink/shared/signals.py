from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol


class FrameSignal(Protocol):
    def connect(self, slot: Callable[[object], Any]) -> Any: ...
