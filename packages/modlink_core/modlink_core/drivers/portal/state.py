from __future__ import annotations

from modlink_qt import QObject, pyqtSignal


class DeviceState(QObject):
    sig_state_changed = pyqtSignal(object)
    sig_connection_lost = pyqtSignal(object)

    def __init__(
        self,
        *,
        device_id: str,
        display_name: str,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self._device_id = device_id
        self._display_name = display_name
        self._is_connected = False
        self._is_streaming = False

    @property
    def device_id(self) -> str:
        return self._device_id

    @property
    def display_name(self) -> str:
        return self._display_name

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    @property
    def is_streaming(self) -> bool:
        return self._is_streaming

    def _mark_connected(self) -> None:
        self._set_state(is_connected=True)

    def _mark_disconnected(self) -> None:
        self._set_state(is_connected=False, is_streaming=False)

    def _mark_streaming_started(self) -> None:
        self._set_state(is_connected=True, is_streaming=True)

    def _mark_streaming_stopped(self) -> None:
        self._set_state(is_streaming=False)

    def _mark_connection_lost(self, detail: object) -> None:
        self._mark_disconnected()
        self.sig_connection_lost.emit(detail)

    def _set_state(
        self,
        *,
        is_connected: bool | None = None,
        is_streaming: bool | None = None,
    ) -> None:
        next_is_connected = (
            self._is_connected if is_connected is None else bool(is_connected)
        )
        next_is_streaming = (
            self._is_streaming if is_streaming is None else bool(is_streaming)
        )
        if next_is_streaming and not next_is_connected:
            raise ValueError("streaming requires the device to be connected")
        if (
            next_is_connected == self._is_connected
            and next_is_streaming == self._is_streaming
        ):
            return
        self._is_connected = next_is_connected
        self._is_streaming = next_is_streaming
        self.sig_state_changed.emit(self)
