from __future__ import annotations

from collections.abc import Callable, Iterable
from threading import RLock
from typing import TypeAlias

from modlink_sdk import FrameEnvelope, StreamDescriptor

from ..events import (
    BackendErrorEvent,
    BackendEventQueue,
    FrameArrivedEvent,
    StreamDescriptorRegisteredEvent,
)

FrameSink: TypeAlias = Callable[[FrameEnvelope], None]
DescriptorSink: TypeAlias = Callable[[StreamDescriptor], None]


class FrameSubscription:
    """Handle returned by ``StreamBus.subscribe_frames``."""

    def __init__(self, bus: StreamBus, sink: FrameSink) -> None:
        self._bus = bus
        self._sink = sink
        self._active = True

    @property
    def active(self) -> bool:
        return self._active

    def close(self) -> None:
        if not self._active:
            return
        self._bus._unsubscribe_frame(self._sink)
        self._active = False

    def unsubscribe(self) -> None:
        self.close()


class DescriptorSubscription:
    """Handle returned by ``StreamBus.subscribe_descriptors``."""

    def __init__(self, bus: StreamBus, sink: DescriptorSink) -> None:
        self._bus = bus
        self._sink = sink
        self._active = True

    @property
    def active(self) -> bool:
        return self._active

    def close(self) -> None:
        if not self._active:
            return
        self._bus._unsubscribe_descriptor(self._sink)
        self._active = False

    def unsubscribe(self) -> None:
        self.close()


class StreamBus:
    """Stores stream descriptors and broadcasts every accepted frame."""

    def __init__(
        self,
        *,
        event_queue: BackendEventQueue,
        parent: object | None = None,
    ) -> None:
        self._event_queue = event_queue
        self._parent = parent
        self._descriptors: dict[str, StreamDescriptor] = {}
        self._frame_sinks: list[FrameSink] = []
        self._descriptor_sinks: list[DescriptorSink] = []
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
        self._event_queue.publish(
            StreamDescriptorRegisteredEvent(descriptor=descriptor)
        )
        with self._lock:
            sinks = tuple(self._descriptor_sinks)
        for sink in sinks:
            sink(descriptor)

    def add_descriptors(self, descriptors: Iterable[StreamDescriptor]) -> None:
        for descriptor in descriptors:
            self.add_descriptor(descriptor)

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

        self._event_queue.publish(FrameArrivedEvent(frame=frame))
        with self._lock:
            sinks = tuple(self._frame_sinks)
        for sink in sinks:
            sink(frame)

    def subscribe_frames(self, sink: FrameSink) -> FrameSubscription:
        if not callable(sink):
            raise TypeError("frame sink must be callable")
        with self._lock:
            if sink not in self._frame_sinks:
                self._frame_sinks.append(sink)
        return FrameSubscription(self, sink)

    def subscribe_descriptors(self, sink: DescriptorSink) -> DescriptorSubscription:
        if not callable(sink):
            raise TypeError("descriptor sink must be callable")
        with self._lock:
            if sink not in self._descriptor_sinks:
                self._descriptor_sinks.append(sink)
        return DescriptorSubscription(self, sink)

    def descriptor(self, stream_id: str) -> StreamDescriptor | None:
        return self._descriptors.get(stream_id)

    def descriptors(self) -> dict[str, StreamDescriptor]:
        return dict(self._descriptors)

    def _unsubscribe_frame(self, sink: FrameSink) -> None:
        with self._lock:
            try:
                self._frame_sinks.remove(sink)
            except ValueError:
                pass

    def _unsubscribe_descriptor(self, sink: DescriptorSink) -> None:
        with self._lock:
            try:
                self._descriptor_sinks.remove(sink)
            except ValueError:
                pass

    def _publish_error(self, message: str) -> None:
        self._event_queue.publish(
            BackendErrorEvent(source="stream_bus", message=message)
        )
