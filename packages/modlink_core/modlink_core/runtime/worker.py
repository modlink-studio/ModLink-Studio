from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import heapq
import queue
import threading
import time
from itertools import count
from uuid import uuid4


@dataclass(slots=True)
class _ScheduledTimer:
    timer_id: str
    callback: Callable[[], None]
    due_at: float
    canceled: bool = False


class WorkerThread:
    """Runs posted callbacks and timers on one dedicated thread."""

    _STOP = "__stop__"
    _POST = "__post__"
    _SCHEDULE_TIMER = "__schedule_timer__"
    _CANCEL_TIMER = "__cancel_timer__"
    _TIMER_SEQUENCE = count(1)

    def __init__(
        self,
        name: str,
        *,
        on_started: Callable[[], None] | None = None,
        on_stopped: Callable[[], None] | None = None,
        on_exit: Callable[[Exception | None], None] | None = None,
    ) -> None:
        self._name = str(name)
        self._on_started = on_started
        self._on_stopped = on_stopped
        self._on_exit = on_exit
        self._mailbox: queue.Queue[tuple[str, object | None]] | None = None
        self._timers: dict[str, _ScheduledTimer] = {}
        self._timer_heap: list[tuple[float, int, _ScheduledTimer]] = []
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
            mailbox: queue.Queue[tuple[str, object | None]] = queue.Queue()
            self._mailbox = mailbox
            self._timers.clear()
            self._timer_heap.clear()
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

        mailbox.put((self._STOP, None))
        thread.join(max(0, timeout_ms) / 1000.0)
        return not thread.is_alive()

    def post(self, callback: Callable[[], None]) -> bool:
        if not callable(callback):
            raise TypeError("worker callback must be callable")
        with self._lock:
            mailbox = self._mailbox
            thread = self._thread
            running = self._running and thread is not None and thread.is_alive()
        if mailbox is None or not running:
            return False
        mailbox.put((self._POST, callback))
        return True

    def call_later(
        self,
        delay_ms: float,
        callback: Callable[[], None],
    ) -> str:
        if not callable(callback):
            raise TypeError("timer callback must be callable")
        timer_id = uuid4().hex
        with self._lock:
            mailbox = self._mailbox
            thread = self._thread
            running = self._running and thread is not None and thread.is_alive()
        if mailbox is None or not running:
            return timer_id
        mailbox.put(
            (
                self._SCHEDULE_TIMER,
                (timer_id, max(0.0, float(delay_ms)), callback),
            )
        )
        return timer_id

    def cancel_timer(self, timer_id: str) -> None:
        with self._lock:
            mailbox = self._mailbox
            thread = self._thread
            running = self._running and thread is not None and thread.is_alive()
        if mailbox is None or not running:
            return
        mailbox.put((self._CANCEL_TIMER, str(timer_id)))

    def _run(self, mailbox: queue.Queue[tuple[str, object | None]]) -> None:
        exit_error: Exception | None = None
        try:
            if self._on_started is not None:
                self._on_started()

            while True:
                self._run_due_timers()
                try:
                    action, payload = mailbox.get(
                        timeout=self._next_timer_timeout_seconds()
                    )
                except queue.Empty:
                    continue

                if action == self._STOP:
                    break
                if action == self._POST:
                    callback = payload
                    if callable(callback):
                        callback()
                    continue
                if action == self._SCHEDULE_TIMER:
                    self._schedule_timer(payload)
                    continue
                if action == self._CANCEL_TIMER:
                    self._cancel_timer_worker(payload)
        except Exception as exc:
            exit_error = exc
        finally:
            if self._on_stopped is not None:
                try:
                    self._on_stopped()
                except Exception as exc:
                    if exit_error is None:
                        exit_error = exc

            with self._lock:
                self._running = False
                self._thread = None
                if self._mailbox is mailbox:
                    self._mailbox = None
                self._timers.clear()
                self._timer_heap.clear()

            if self._on_exit is not None:
                self._on_exit(exit_error)

    def _schedule_timer(self, payload: object) -> None:
        if not isinstance(payload, tuple) or len(payload) != 3:
            return
        timer_id, delay_ms, callback = payload
        if not callable(callback):
            return
        try:
            delay_seconds = max(0.0, float(delay_ms) / 1000.0)
        except (TypeError, ValueError):
            delay_seconds = 0.0
        scheduled_timer = _ScheduledTimer(
            timer_id=str(timer_id),
            callback=callback,
            due_at=time.monotonic() + delay_seconds,
        )
        self._timers[scheduled_timer.timer_id] = scheduled_timer
        heapq.heappush(
            self._timer_heap,
            (
                scheduled_timer.due_at,
                next(self._TIMER_SEQUENCE),
                scheduled_timer,
            ),
        )

    def _cancel_timer_worker(self, payload: object) -> None:
        if payload is None:
            return
        scheduled_timer = self._timers.pop(str(payload), None)
        if scheduled_timer is not None:
            scheduled_timer.canceled = True

    def _run_due_timers(self) -> None:
        while True:
            next_timer = self._peek_next_timer()
            if next_timer is None or next_timer.due_at > time.monotonic():
                return
            heapq.heappop(self._timer_heap)
            current_timer = self._timers.get(next_timer.timer_id)
            if current_timer is not next_timer or next_timer.canceled:
                continue
            self._timers.pop(next_timer.timer_id, None)
            next_timer.callback()

    def _next_timer_timeout_seconds(self) -> float | None:
        next_timer = self._peek_next_timer()
        if next_timer is None:
            return None
        return max(0.0, next_timer.due_at - time.monotonic())

    def _peek_next_timer(self) -> _ScheduledTimer | None:
        while self._timer_heap:
            _, _, scheduled_timer = self._timer_heap[0]
            current_timer = self._timers.get(scheduled_timer.timer_id)
            if current_timer is not scheduled_timer or scheduled_timer.canceled:
                heapq.heappop(self._timer_heap)
                continue
            return scheduled_timer
        return None
