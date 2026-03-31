from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import Future
from threading import RLock

from ...runtime.worker import WorkerThread


class DriverExecutor:
    """Runs submitted callables on one dedicated Python thread."""

    def __init__(
        self,
        name: str,
        *,
        on_exit: Callable[[Exception | None], None] | None = None,
    ) -> None:
        self._name = str(name)
        self._on_exit = on_exit
        self._pending: set[Future[object | None]] = set()
        self._lock = RLock()
        self._worker = WorkerThread(
            self._name,
            on_exit=self._on_worker_exit,
        )

    @property
    def is_running(self) -> bool:
        return self._worker.is_running

    def start(self) -> None:
        self._worker.start()

    def stop(self, *, timeout_ms: int = 3000) -> bool:
        return self._worker.stop(timeout_ms=timeout_ms)

    def submit(
        self,
        callback: Callable[..., object | None],
        *args: object,
        **kwargs: object,
    ) -> Future[object | None]:
        future: Future[object | None] = Future()
        if not self.is_running:
            future.set_exception(
                RuntimeError(f"{self._name} is not running")
            )
            return future

        with self._lock:
            self._pending.add(future)
        posted = self._worker.post(
            lambda: self._execute_future(future, callback, args, kwargs)
        )
        if posted:
            return future

        with self._lock:
            self._pending.discard(future)
        if not future.done():
            future.set_exception(
                RuntimeError(
                    f"{self._name} stopped before task could be posted"
                )
            )
        return future

    def _execute_future(
        self,
        future: Future[object | None],
        callback: Callable[..., object | None],
        args: tuple[object, ...],
        kwargs: dict[str, object],
    ) -> None:
        if not future.set_running_or_notify_cancel():
            self._discard_future(future)
            return

        try:
            result = callback(*args, **kwargs)
        except Exception as exc:
            future.set_exception(exc)
        else:
            future.set_result(result)
        finally:
            self._discard_future(future)

    def _discard_future(self, future: Future[object | None]) -> None:
        with self._lock:
            self._pending.discard(future)

    def _fail_pending_futures(
        self,
        stop_reason: Exception | None,
    ) -> None:
        with self._lock:
            pending = list(self._pending)
            self._pending.clear()

        if not pending:
            return

        if stop_reason is None:
            message = f"{self._name} stopped before pending tasks completed"
        else:
            message = (
                f"{self._name} stopped before pending tasks completed: "
                f"{type(stop_reason).__name__}: {stop_reason}"
            )

        for future in pending:
            if future.done():
                continue
            future.set_exception(RuntimeError(message))

    def _on_worker_exit(self, stop_reason: Exception | None) -> None:
        self._fail_pending_futures(stop_reason)
        if self._on_exit is not None:
            self._on_exit(stop_reason)
