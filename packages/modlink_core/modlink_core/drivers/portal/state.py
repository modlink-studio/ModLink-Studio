from __future__ import annotations

from threading import RLock


class DeviceState:
    def __init__(
        self,
        *,
        device_id: str,
        display_name: str,
        parent: object | None = None,
    ) -> None:
        self._parent = parent
        self._device_id = device_id
        self._display_name = display_name
        self._lock = RLock()
        self._is_connected = False
        self._is_streaming = False

    @property
    def device_id(self) -> str:
        with self._lock:
            return self._device_id

    @property
    def display_name(self) -> str:
        with self._lock:
            return self._display_name

    @property
    def is_connected(self) -> bool:
        with self._lock:
            return self._is_connected

    @property
    def is_streaming(self) -> bool:
        with self._lock:
            return self._is_streaming

    def snapshot(self) -> tuple[bool, bool]:
        with self._lock:
            return self._is_connected, self._is_streaming

    def _mark_connected(self) -> bool:
        return self._set_state(is_connected=True)

    def _mark_disconnected(self) -> bool:
        return self._set_state(
            is_connected=False,
            is_streaming=False,
        )

    def _mark_streaming_started(self) -> bool:
        return self._set_state(
            is_connected=True,
            is_streaming=True,
        )

    def _mark_streaming_stopped(self) -> bool:
        return self._set_state(is_streaming=False)

    def _mark_connection_lost(self) -> bool:
        return self._set_state(is_connected=False, is_streaming=False)

    def _set_state(
        self,
        *,
        is_connected: bool | None = None,
        is_streaming: bool | None = None,
    ) -> bool:
        with self._lock:
            next_is_connected = self._is_connected if is_connected is None else bool(is_connected)
            next_is_streaming = self._is_streaming if is_streaming is None else bool(is_streaming)
            if next_is_streaming and not next_is_connected:
                raise ValueError("streaming requires the device to be connected")
            if next_is_connected == self._is_connected and next_is_streaming == self._is_streaming:
                return False
            self._is_connected = next_is_connected
            self._is_streaming = next_is_streaming
            return True
