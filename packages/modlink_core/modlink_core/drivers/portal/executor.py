from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import Future
import queue
import threading


class DriverExecutor:
    """Runs submitted callables on one dedicated Python thread."""

    _STOP = object()

    def __init__(
        self,
        name: str,
        *,
        on_exit: Callable[[Exception | None], None] | None = None,
    ) -> None:
        self._name = str(name)
        self._on_exit = on_exit
        self._pending: set[Future[object | None]] = set()
        self._mailbox: queue.Queue[Callable[[], None] | object] | None = None
        self._thread: threading.Thread | None = None
        self._running = False
        self._lock = threading.RLock()

    @property
    def is_running(self) -> bool:
        with self._lock:
            thread = self._thread
            return self._running and thread is not None and thread.is_alive()

    def start(self) -> None:
        with self._lock:
            if self.is_running:
                return
            mailbox: queue.Queue[Callable[[], None] | object] = queue.Queue()
            self._mailbox = mailbox
            self._running = True
            thread = threading.Thread(
                target=self._run,
                args=(mailbox,),
                name=self._name,
                daemon=True,
            )
            self._thread = thread
            thread.start()

    def stop(self, *, timeout_ms: int = 3000) -> bool:
        with self._lock:
            thread = self._thread
            mailbox = self._mailbox
        if thread is None or not thread.is_alive() or mailbox is None:
            with self._lock:
                self._running = False
                self._thread = None
                self._mailbox = None
            return True

        mailbox.put(self._STOP)
        thread.join(max(0, timeout_ms) / 1000.0)
        return not thread.is_alive()

    def submit(
        self,
        callback: Callable[..., object | None],
        *args: object,
        **kwargs: object,
    ) -> Future[object | None]:
        future: Future[object | None] = Future()
        if not self.is_running:
            future.set_exception(RuntimeError(f"{self._name} is not running"))
            return future

        with self._lock:
            mailbox = self._mailbox
            self._pending.add(future)
        if mailbox is None:
            self._discard_future(future)
            future.set_exception(RuntimeError(f"{self._name} is not running"))
            return future

        mailbox.put(lambda: self._execute_future(future, callback, args, kwargs))
        return future

    def _run(self, mailbox: queue.Queue[Callable[[], None] | object]) -> None:
        exit_error: Exception | None = None
        try:
            while True:
                item = mailbox.get()
                if item is self._STOP:
                    break
                if callable(item):
                    item()
        except Exception as exc:
            exit_error = exc
        finally:
            with self._lock:
                self._running = False
                self._thread = None
                if self._mailbox is mailbox:
                    self._mailbox = None
            self._fail_pending_futures(exit_error)
            if self._on_exit is not None:
                self._on_exit(exit_error)

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

    def _fail_pending_futures(self, stop_reason: Exception | None) -> None:
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
