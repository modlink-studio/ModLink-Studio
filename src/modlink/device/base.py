from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal

from ..shared import FrameSignal, StreamDescriptor


class Device(QObject):
    """Base contract that all ModLink devices/drivers must implement.

    A concrete driver is expected to live in its own QThread.

    Contract summary:
    - expose one low-frequency ``sig_event`` for search/status/error style events
    - expose one frame signal per stream
    - keep transport/search/streaming logic inside the driver itself
    - do not depend on bus internals
    """

    sig_event = pyqtSignal(object)

    def _not_implemented(self, member: str) -> None:
        raise NotImplementedError(
            f"{type(self).__name__} must implement Device.{member}"
        )

    @property
    def device_id(self) -> str:
        self._not_implemented("device_id")

    @property
    def display_name(self) -> str:
        return self.device_id

    def stream_descriptors(self) -> tuple[StreamDescriptor, ...]:
        self._not_implemented("stream_descriptors")

    def frame_signal(self, stream_id: str) -> FrameSignal:
        self._not_implemented("frame_signal")

    def frame_signals(self) -> dict[str, FrameSignal]:
        return {
            descriptor.stream_id: self.frame_signal(descriptor.stream_id)
            for descriptor in self.stream_descriptors()
        }

    def search(self, request: object | None = None) -> None:
        self._not_implemented("search")

    def connect_device(self, config: object | None = None) -> None:
        self._not_implemented("connect_device")

    def disconnect_device(self) -> None:
        self._not_implemented("disconnect_device")

    def start_streaming(self) -> None:
        self._not_implemented("start_streaming")

    def stop_streaming(self) -> None:
        self._not_implemented("stop_streaming")
