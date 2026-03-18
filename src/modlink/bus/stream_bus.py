from __future__ import annotations

from collections.abc import Callable
from typing import TypeAlias

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from ..shared import FrameEnvelope, FrameSignal, StreamDescriptor

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
        except (TypeError, RuntimeError):
            pass
        self._active = False

    def unsubscribe(self) -> None:
        self.close()


class StreamBus(QObject):
    """Registers streams and broadcasts every accepted frame to subscribers."""

    sig_stream_descriptor = pyqtSignal(object)
    sig_frame = pyqtSignal(object)
    sig_error = pyqtSignal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent=parent)
        self._descriptors: dict[str, StreamDescriptor] = {}
        self._frame_signals: dict[str, FrameSignal] = {}

    def register_stream(
        self, descriptor: StreamDescriptor, frame_signal: FrameSignal
    ) -> None:
        existing_descriptor = self._descriptors.get(descriptor.stream_id)
        existing_signal = self._frame_signals.get(descriptor.stream_id)
        if existing_descriptor is not None:
            if existing_descriptor == descriptor and existing_signal is frame_signal:
                return

            self.sig_error.emit(
                f"DUPLICATE_STREAM_DESCRIPTOR: conflicting registration for stream_id={descriptor.stream_id}"
            )
            raise ValueError(
                f"conflicting descriptor for stream_id '{descriptor.stream_id}'"
            )

        self._descriptors[descriptor.stream_id] = descriptor
        self._frame_signals[descriptor.stream_id] = frame_signal
        frame_signal.connect(self.publish_frame)
        self.sig_stream_descriptor.emit(descriptor)

    @pyqtSlot(object)
    def publish_frame(self, frame: object) -> None:
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

    def subscribe(self, sink: FrameSink) -> FrameSubscription:
        self.sig_frame.connect(sink)
        return FrameSubscription(self, sink)

    def descriptor(self, stream_id: str) -> StreamDescriptor | None:
        return self._descriptors.get(stream_id)

    def descriptors(self) -> dict[str, StreamDescriptor]:
        return dict(self._descriptors)
