"""Small thread-safe signal primitive used by the pure Python runtime."""

from __future__ import annotations

from collections.abc import Callable
from threading import RLock
from typing import Any


class Signal:
    """Minimal connect/emit API compatible with the project's prior usage."""

    def __init__(self) -> None:
        self._callbacks: list[Callable[..., Any]] = []
        self._lock = RLock()

    def connect(self, callback: Callable[..., Any], *_args: object) -> None:
        if not callable(callback):
            raise TypeError("signal callback must be callable")
        with self._lock:
            if callback not in self._callbacks:
                self._callbacks.append(callback)

    def disconnect(self, callback: Callable[..., Any]) -> None:
        with self._lock:
            try:
                self._callbacks.remove(callback)
            except ValueError as exc:
                raise TypeError("signal callback is not connected") from exc

    def emit(self, *args: Any, **kwargs: Any) -> None:
        with self._lock:
            callbacks = tuple(self._callbacks)
        for callback in callbacks:
            callback(*args, **kwargs)
