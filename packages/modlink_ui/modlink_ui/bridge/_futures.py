from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import CancelledError, Future
from typing import TypeVar

_T = TypeVar("_T")


def watch_future_completion(
    future: Future[_T],
    *,
    on_success: Callable[[_T], None],
    on_error: Callable[[str], None],
    cancelled_message: str,
) -> None:
    """Route Future completion through thread-safe emitters."""

    def _notify_completed(completed: Future[_T]) -> None:
        try:
            result = completed.result()
        except CancelledError:
            on_error(cancelled_message)
            return
        except Exception as exc:
            on_error(str(exc))
            return
        on_success(result)

    if future.done():
        _notify_completed(future)
        return
    future.add_done_callback(_notify_completed)
