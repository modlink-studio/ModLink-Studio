from __future__ import annotations

import queue
from dataclasses import dataclass
from threading import RLock
from typing import Any, Literal, TypeAlias

class StreamClosedError(Exception):
    """Raised when a blocking stream read is interrupted by stream closure."""


@dataclass(frozen=True, slots=True)
class DriverSnapshot:
    driver_id: str
    display_name: str
    supported_providers: tuple[str, ...]
    is_running: bool
    is_connected: bool
    is_streaming: bool


@dataclass(frozen=True, slots=True)
class AcquisitionSnapshot:
    state: str
    is_started: bool
    is_recording: bool
    root_dir: str


@dataclass(frozen=True, slots=True)
class DriverConnectionLostEvent:
    driver_id: str
    detail: object | None = None
    kind: Literal["driver_connection_lost"] = "driver_connection_lost"


@dataclass(frozen=True, slots=True)
class AcquisitionStateChangedEvent:
    snapshot: AcquisitionSnapshot
    kind: Literal["acquisition_state_changed"] = "acquisition_state_changed"


@dataclass(frozen=True, slots=True)
class AcquisitionErrorEvent:
    message: str
    kind: Literal["acquisition_error"] = "acquisition_error"


@dataclass(frozen=True, slots=True)
class AcquisitionLifecycleEvent:
    name: str
    payload: dict[str, object]
    kind: Literal["acquisition_lifecycle"] = "acquisition_lifecycle"


@dataclass(frozen=True, slots=True)
class SettingChangedEvent:
    key: str
    value: Any
    ts: float
    kind: Literal["setting_changed"] = "setting_changed"


@dataclass(frozen=True, slots=True)
class BackendErrorEvent:
    """Low-frequency backend infrastructure failure."""

    source: str
    message: str
    kind: Literal["backend_error"] = "backend_error"


BackendEvent: TypeAlias = (
    DriverConnectionLostEvent
    | AcquisitionStateChangedEvent
    | AcquisitionErrorEvent
    | AcquisitionLifecycleEvent
    | SettingChangedEvent
    | BackendErrorEvent
)

_STREAM_CLOSED = object()


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

            overflow_event = BackendErrorEvent(
                source="event_stream",
                message="EVENT_STREAM_OVERFLOW",
            )
            try:
                self._queue.put_nowait(overflow_event)
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
