from __future__ import annotations

import time
import uuid
from collections.abc import Callable

from PyQt6.QtCore import QObject, pyqtSignal

from .models import FrameEnvelope, PlatformErrorEvent, StreamDescriptor


class StreamBus(QObject):
    """Transport-agnostic frame bus with per-stream subscription support."""

    sig_stream_descriptor = pyqtSignal(object)
    sig_frame = pyqtSignal(object)
    sig_error = pyqtSignal(object)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent=parent)
        self._descriptors: dict[str, StreamDescriptor] = {}
        self._stream_subscribers: dict[
            str, dict[str, Callable[[FrameEnvelope], None]]
        ] = {}
        self._global_subscribers: dict[str, Callable[[FrameEnvelope], None]] = {}

    def attach_device(self, device) -> None:
        device.sig_stream_descriptor.connect(self.register_stream)
        device.sig_frame.connect(self.publish_frame)
        device.sig_error.connect(self.sig_error.emit)

    def register_stream(self, descriptor: StreamDescriptor) -> None:
        existing = self._descriptors.get(descriptor.stream_id)
        if existing is not None and existing != descriptor:
            self.sig_error.emit(
                PlatformErrorEvent(
                    code="DUPLICATE_STREAM_DESCRIPTOR",
                    message="conflicting stream descriptor received",
                    ts=time.time(),
                    origin="stream_bus",
                    detail=descriptor.stream_id,
                    recoverable=False,
                )
            )
            return

        self._descriptors[descriptor.stream_id] = descriptor
        self._stream_subscribers.setdefault(descriptor.stream_id, {})
        self.sig_stream_descriptor.emit(descriptor)

    def publish_frame(self, frame: FrameEnvelope) -> None:
        if frame.stream_id not in self._descriptors:
            self.sig_error.emit(
                PlatformErrorEvent(
                    code="UNKNOWN_STREAM",
                    message="frame published before stream registration",
                    ts=time.time(),
                    origin="stream_bus",
                    detail=frame.stream_id,
                )
            )
            return

        self.sig_frame.emit(frame)
        for callback in tuple(self._global_subscribers.values()):
            callback(frame)
        for callback in tuple(
            self._stream_subscribers.get(frame.stream_id, {}).values()
        ):
            callback(frame)

    def subscribe(
        self,
        stream_id: str,
        callback: Callable[[FrameEnvelope], None],
    ) -> str:
        token = uuid.uuid4().hex
        self._stream_subscribers.setdefault(stream_id, {})[token] = callback
        return token

    def subscribe_all(self, callback: Callable[[FrameEnvelope], None]) -> str:
        token = uuid.uuid4().hex
        self._global_subscribers[token] = callback
        return token

    def unsubscribe(self, token: str) -> None:
        if token in self._global_subscribers:
            self._global_subscribers.pop(token, None)
            return

        for subscribers in self._stream_subscribers.values():
            if token in subscribers:
                subscribers.pop(token, None)
                return

    def descriptor(self, stream_id: str) -> StreamDescriptor | None:
        return self._descriptors.get(stream_id)

    def descriptors(self) -> tuple[StreamDescriptor, ...]:
        return tuple(self._descriptors.values())
