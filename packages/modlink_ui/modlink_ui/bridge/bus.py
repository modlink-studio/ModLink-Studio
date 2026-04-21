from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal

from modlink_core.bus import StreamBus
from modlink_sdk import FrameEnvelope, StreamDescriptor


class QtBusBridge(QObject):
    sig_frames = pyqtSignal(object)
    sig_frame = pyqtSignal(object)
    sig_error = pyqtSignal(str)

    def __init__(self, bus: StreamBus, parent: QObject | None = None) -> None:
        super().__init__(parent=parent)
        self._bus = bus
        self._descriptors = bus.descriptors()

    def descriptors(self) -> dict[str, StreamDescriptor]:
        return dict(self._descriptors)

    def descriptor(self, stream_id: str) -> StreamDescriptor | None:
        return self._descriptors.get(stream_id)

    def _set_descriptors(self, descriptors: dict[str, StreamDescriptor]) -> None:
        self._descriptors = dict(descriptors)

    def _emit_frames(self, frames: list[FrameEnvelope]) -> None:
        if not frames:
            return
        self.sig_frames.emit(frames)
        for frame in frames:
            self.sig_frame.emit(frame)

    def _emit_error(self, message: str) -> None:
        self.sig_error.emit(message)
