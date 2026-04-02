from __future__ import annotations

import queue
from threading import RLock

from .events import BackendEvent


class StreamClosedError(Exception):
    """Raised when a blocking stream read is interrupted by stream closure."""


class EventStreamOverflowError(Exception):
    """Raised when the low-frequency event stream overflows."""


_STREAM_CLOSED = object()
_STREAM_OVERFLOW = object()


class EventStream:
    def __init__(
        self,
        broker: BackendEventBroker,
        *,
        maxsize: int = 1024,
    ) -> None:
        normalized_maxsize = max(1, int(maxsize))
        self._broker = broker
        self._queue: queue.Queue[BackendEvent | object] = queue.Queue(
            maxsize=normalized_maxsize
        )
        self._lock = RLock()
        self._closed = False

    @property
    def closed(self) -> bool:
        return self._closed

    def read(
        self,
        *,
        block: bool = True,
        timeout: float | None = None,
    ) -> BackendEvent:
        item = self._queue.get(block=block, timeout=timeout)
        if item is _STREAM_CLOSED:
            raise StreamClosedError("event stream is closed")
        if item is _STREAM_OVERFLOW:
            raise EventStreamOverflowError("event stream overflowed")
        return item  # type: ignore[return-value]

    def read_many(self, *, max_items: int | None = None) -> list[BackendEvent]:
        if max_items is not None and max_items <= 0:
            return []

        items: list[BackendEvent] = []
        while max_items is None or len(items) < max_items:
            try:
                item = self._queue.get_nowait()
            except queue.Empty:
                break
            if item is _STREAM_CLOSED:
                if items:
                    return items
                raise StreamClosedError("event stream is closed")
            if item is _STREAM_OVERFLOW:
                if items:
                    return items
                raise EventStreamOverflowError("event stream overflowed")
            items.append(item)  # type: ignore[arg-type]
        return items

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
        self._broker._close_stream(self)

    def _publish(self, event: BackendEvent) -> None:
        with self._lock:
            if self._closed:
                return
            try:
                self._queue.put_nowait(event)
                return
            except queue.Full:
                pass

            try:
                self._queue.get_nowait()
            except queue.Empty:
                pass

            try:
                self._queue.put_nowait(_STREAM_OVERFLOW)
            except queue.Full:
                pass

    def _push_closed(self) -> None:
        with self._lock:
            try:
                self._queue.put_nowait(_STREAM_CLOSED)
                return
            except queue.Full:
                pass

            try:
                self._queue.get_nowait()
            except queue.Empty:
                pass

            try:
                self._queue.put_nowait(_STREAM_CLOSED)
            except queue.Full:
                pass


class BackendEventBroker:
    def __init__(self) -> None:
        self._streams: list[EventStream] = []
        self._lock = RLock()

    def open_stream(self, *, maxsize: int = 1024) -> EventStream:
        stream = EventStream(self, maxsize=maxsize)
        with self._lock:
            self._streams.append(stream)
        return stream

    def publish(self, event: BackendEvent) -> None:
        with self._lock:
            streams = tuple(self._streams)
        for stream in streams:
            stream._publish(event)

    def _close_stream(self, stream: EventStream) -> None:
        with self._lock:
            try:
                self._streams.remove(stream)
            except ValueError:
                pass
        stream._push_closed()
