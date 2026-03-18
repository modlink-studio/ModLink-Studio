from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal


class Device(QObject):
    """Device runtime port for the new ModLink Studio architecture."""

    sig_stream_descriptor = pyqtSignal(object)
    sig_frame = pyqtSignal(object)
    sig_status = pyqtSignal(object)
    sig_error = pyqtSignal(object)

    def _not_implemented(self, member: str) -> None:
        raise NotImplementedError(
            f"{type(self).__name__} must implement Device.{member}"
        )

    @property
    def device_id(self) -> str:
        self._not_implemented("device_id")

    def connect_device(self) -> None:
        self._not_implemented("connect_device")

    def disconnect_device(self) -> None:
        self._not_implemented("disconnect_device")

    def start_streaming(self) -> None:
        self._not_implemented("start_streaming")

    def stop_streaming(self) -> None:
        self._not_implemented("stop_streaming")
