from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtCore import QObject, pyqtBoundSignal, pyqtSignal

from packages.modlink_shared import StreamDescriptor


class Driver(QObject):
    sig_event = pyqtSignal(object)

    @property
    def device_id(self) -> str:
        raise NotImplementedError(f"{type(self).__name__} must implement device_id")

    @property
    def display_name(self) -> str:
        return self.device_id

    def on_thread_started(self) -> None:
        """Optional hook invoked after the driver thread starts."""

    def streams(self) -> list[tuple[StreamDescriptor, pyqtBoundSignal]]:
        raise NotImplementedError(f"{type(self).__name__} must implement streams")

    def shutdown(self) -> None:
        try:
            self.stop_streaming()
        except NotImplementedError:
            pass

        try:
            self.disconnect_device()
        except NotImplementedError:
            pass

    def search(self, request: object | None = None) -> None:
        raise NotImplementedError(f"{type(self).__name__} must implement search")

    def connect_device(self, config: object | None = None) -> None:
        raise NotImplementedError(
            f"{type(self).__name__} must implement connect_device if it supports connecting"
        )

    def disconnect_device(self) -> None:
        raise NotImplementedError(
            f"{type(self).__name__} must implement disconnect_device if it supports connecting"
        )

    def start_streaming(self) -> None:
        raise NotImplementedError(
            f"{type(self).__name__} must implement start_streaming"
        )

    def stop_streaming(self) -> None:
        raise NotImplementedError(
            f"{type(self).__name__} must implement stop_streaming"
        )

DriverFactory = Callable[[], Driver]
