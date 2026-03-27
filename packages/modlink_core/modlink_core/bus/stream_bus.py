from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import TypeAlias

from modlink_sdk import FrameEnvelope, StreamDescriptor
from modlink_sdk.signals import Signal

FrameSink: TypeAlias = Callable[[FrameEnvelope], None]


class FrameSubscription:
    """Handle returned by ``StreamBus.subscribe``."""

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
        try:
            self._bus.sig_frame.disconnect(self._sink)
        except TypeError:
            pass
        self._active = False

    def unsubscribe(self) -> None:
        self.close()


class StreamBus:
    """Stores stream descriptors and broadcasts every accepted frame."""

    def __init__(self, parent: object | None = None) -> None:
        self.sig_stream_descriptor = Signal()
        self.sig_frame = Signal()
        self.sig_error = Signal()
        self._parent = parent
        self._descriptors: dict[str, StreamDescriptor] = {}

    def add_descriptor(self, descriptor: StreamDescriptor) -> None:
        existing_descriptor = self._descriptors.get(descriptor.stream_id)
        if existing_descriptor is not None:
            if existing_descriptor == descriptor:
                return

            self.sig_error.emit(
                f"DUPLICATE_STREAM_DESCRIPTOR: conflicting registration for stream_id={descriptor.stream_id}"
            )
            raise ValueError(
                f"conflicting descriptor for stream_id '{descriptor.stream_id}'"
            )

        self._descriptors[descriptor.stream_id] = descriptor
        self.sig_stream_descriptor.emit(descriptor)

    def add_descriptors(self, descriptors: Iterable[StreamDescriptor]) -> None:
        for descriptor in descriptors:
            self.add_descriptor(descriptor)

    def ingest_frame(self, frame: object) -> None:
        if not isinstance(frame, FrameEnvelope):
            self.sig_error.emit(
                f"INVALID_FRAME: expected FrameEnvelope, got {type(frame).__name__}"
            )
            return

        if frame.stream_id not in self._descriptors:
            self.sig_error.emit(
                f"UNKNOWN_STREAM: frame published before stream registration for stream_id={frame.stream_id}"
            )
            return

        self.sig_frame.emit(frame)

    def subscribe(
        self,
        sink: FrameSink,
        *,
        connection_type: object | None = None,
    ) -> FrameSubscription:
        _ = connection_type
        self.sig_frame.connect(sink)
        return FrameSubscription(self, sink)

    def descriptor(self, stream_id: str) -> StreamDescriptor | None:
        return self._descriptors.get(stream_id)

    def descriptors(self) -> dict[str, StreamDescriptor]:
        return dict(self._descriptors)
