from __future__ import annotations

import queue
from collections.abc import Iterable
from itertools import count
from threading import RLock
from typing import Literal

from modlink_sdk import FrameEnvelope, StreamDescriptor

from ..events import BackendErrorEvent, BackendEventBroker
from ..events import StreamClosedError

FrameDropPolicy = Literal["drop_oldest", "error"]

_FRAME_STREAM_CLOSED = object()
_FRAME_STREAM_OVERFLOW = object()


class FrameStreamOverflowError(Exception):
    def __init__(self, consumer_name: str) -> None:
        self.consumer_name = consumer_name
        super().__init__(f"frame stream overflowed: consumer_name={consumer_name}")


class FrameStream:
    def __init__(
        self,
        bus: StreamBus,
        *,
        maxsize: int = 256,
        drop_policy: FrameDropPolicy = "drop_oldest",
        consumer_name: str,
    ) -> None:
        if drop_policy not in {"drop_oldest", "error"}:
            raise ValueError(f"unsupported frame drop policy: {drop_policy}")
        normalized_maxsize = max(1, int(maxsize))
        self._bus = bus
        self._queue: queue.Queue[FrameEnvelope | object] = queue.Queue(
            maxsize=normalized_maxsize
        )
        self._drop_policy = drop_policy
        self._consumer_name = consumer_name
        self._dropped_count = 0
        self._closed = False
        self._overflowed = False
        self._lock = RLock()

    @property
    def consumer_name(self) -> str:
        return self._consumer_name

    @property
    def dropped_count(self) -> int:
        return self._dropped_count

    @property
    def overflowed(self) -> bool:
        return self._overflowed

    @property
    def closed(self) -> bool:
        return self._closed

    def read(
        self,
        *,
        block: bool = True,
        timeout: float | None = None,
    ) -> FrameEnvelope:
        item = self._queue.get(block=block, timeout=timeout)
        if item is _FRAME_STREAM_CLOSED:
            raise StreamClosedError("frame stream is closed")
        if item is _FRAME_STREAM_OVERFLOW:
            raise FrameStreamOverflowError(self._consumer_name)
        return item  # type: ignore[return-value]

    def read_many(self, *, max_items: int | None = None) -> list[FrameEnvelope]:
        if max_items is not None and max_items <= 0:
            return []

        items: list[FrameEnvelope] = []
        while max_items is None or len(items) < max_items:
            try:
                item = self._queue.get_nowait()
            except queue.Empty:
                break
            if item is _FRAME_STREAM_CLOSED:
                if items:
                    return items
                raise StreamClosedError("frame stream is closed")
            if item is _FRAME_STREAM_OVERFLOW:
                if items:
                    return items
                raise FrameStreamOverflowError(self._consumer_name)
            items.append(item)  # type: ignore[arg-type]
        return items

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
        self._bus._close_frame_stream(self)

    def _publish(self, frame: FrameEnvelope) -> None:
        with self._lock:
            if self._closed:
                return
            if self._overflowed and self._drop_policy == "error":
                self._dropped_count += 1
                return
            try:
                self._queue.put_nowait(frame)
                return
            except queue.Full:
                self._dropped_count += 1

                if self._drop_policy == "drop_oldest":
                    self._drop_oldest_and_enqueue(frame)
                    return

                self._overflowed = True
                self._clear_queue_locked()
                self._push_control_locked(_FRAME_STREAM_OVERFLOW)

        self._bus._publish_error(
            f"FRAME_STREAM_OVERFLOW:{self._consumer_name}",
            source="frame_stream",
        )

    def _drop_oldest_and_enqueue(self, frame: FrameEnvelope) -> None:
        try:
            self._queue.get_nowait()
        except queue.Empty:
            pass
        try:
            self._queue.put_nowait(frame)
        except queue.Full:
            pass

    def _clear_queue_locked(self) -> None:
        while True:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

    def _push_closed(self) -> None:
        with self._lock:
            self._push_control_locked(_FRAME_STREAM_CLOSED)

    def _push_control_locked(self, item: object) -> None:
        try:
            self._queue.put_nowait(item)
            return
        except queue.Full:
            pass

        try:
            self._queue.get_nowait()
        except queue.Empty:
            pass

        try:
            self._queue.put_nowait(item)
        except queue.Full:
            pass


class StreamBus:
    """Stores stream descriptors and fans out accepted frames to frame streams."""

    _STREAM_COUNTER = count(1)

    def __init__(
        self,
        *,
        event_broker: BackendEventBroker,
        parent: object | None = None,
    ) -> None:
        self._event_broker = event_broker
        self._parent = parent
        self._descriptors: dict[str, StreamDescriptor] = {}
        self._frame_streams: list[FrameStream] = []
        self._lock = RLock()

    def add_descriptor(self, descriptor: StreamDescriptor) -> None:
        existing_descriptor = self._descriptors.get(descriptor.stream_id)
        if existing_descriptor is not None:
            if existing_descriptor == descriptor:
                return

            self._publish_error(
                f"DUPLICATE_STREAM_DESCRIPTOR: conflicting registration for stream_id={descriptor.stream_id}"
            )
            raise ValueError(
                f"conflicting descriptor for stream_id '{descriptor.stream_id}'"
            )

        self._descriptors[descriptor.stream_id] = descriptor

    def add_descriptors(self, descriptors: Iterable[StreamDescriptor]) -> None:
        for descriptor in descriptors:
            self.add_descriptor(descriptor)

    def remove_descriptor(self, stream_id: str) -> None:
        self._descriptors.pop(str(stream_id), None)

    def ingest_frame(self, frame: object) -> None:
        if not isinstance(frame, FrameEnvelope):
            self._publish_error(
                f"INVALID_FRAME: expected FrameEnvelope, got {type(frame).__name__}"
            )
            return

        if frame.stream_id not in self._descriptors:
            self._publish_error(
                f"UNKNOWN_STREAM: frame published before stream registration for stream_id={frame.stream_id}"
            )
            return

        with self._lock:
            streams = tuple(self._frame_streams)
        for stream in streams:
            stream._publish(frame)

    def open_frame_stream(
        self,
        *,
        maxsize: int = 256,
        drop_policy: FrameDropPolicy = "drop_oldest",
        consumer_name: str | None = None,
    ) -> FrameStream:
        stream = FrameStream(
            self,
            maxsize=maxsize,
            drop_policy=drop_policy,
            consumer_name=consumer_name or self._next_consumer_name(),
        )
        with self._lock:
            self._frame_streams.append(stream)
        return stream

    def descriptor(self, stream_id: str) -> StreamDescriptor | None:
        return self._descriptors.get(stream_id)

    def descriptors(self) -> dict[str, StreamDescriptor]:
        return dict(self._descriptors)

    def _close_frame_stream(self, stream: FrameStream) -> None:
        with self._lock:
            try:
                self._frame_streams.remove(stream)
            except ValueError:
                pass
        stream._push_closed()

    def _publish_error(self, message: str, *, source: str = "stream_bus") -> None:
        self._event_broker.publish(BackendErrorEvent(source=source, message=message))

    @classmethod
    def _next_consumer_name(cls) -> str:
        return f"frame_stream_{next(cls._STREAM_COUNTER)}"
