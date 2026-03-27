from __future__ import annotations


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
        self._is_connected = False
        self._is_streaming = False
        self._status = "disconnected"
        self._status_detail: object | None = None

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

    @property
    def status(self) -> str:
        return self._status

    @property
    def status_detail(self) -> object | None:
        return self._status_detail

    def _mark_connected(self) -> None:
        self._set_state(is_connected=True, status="connected", status_detail=None)

    def _mark_disconnected(self) -> None:
        self._set_state(
            is_connected=False,
            is_streaming=False,
            status="disconnected",
            status_detail=None,
        )

    def _mark_streaming_started(self) -> None:
        self._set_state(
            is_connected=True,
            is_streaming=True,
            status="streaming",
            status_detail=None,
        )

    def _mark_streaming_stopped(self) -> None:
        self._set_state(
            is_streaming=False,
            status="connected" if self._is_connected else "disconnected",
            status_detail=None,
        )

    def _mark_connection_lost(self, detail: object) -> None:
        self._set_state(
            is_connected=False,
            is_streaming=False,
            status="connection_lost",
            status_detail=detail,
        )

    def _mark_status(self, status: str, detail: object | None) -> None:
        self._set_state(status=status, status_detail=detail)

    def _set_state(
        self,
        *,
        is_connected: bool | None = None,
        is_streaming: bool | None = None,
        status: str | None = None,
        status_detail: object | None = None,
    ) -> None:
        next_is_connected = (
            self._is_connected if is_connected is None else bool(is_connected)
        )
        next_is_streaming = (
            self._is_streaming if is_streaming is None else bool(is_streaming)
        )
        next_status = self._status if status is None else str(status).strip()
        next_status_detail = (
            self._status_detail if status is None else status_detail
        )
        if next_is_streaming and not next_is_connected:
            raise ValueError("streaming requires the device to be connected")
        if (
            next_is_connected == self._is_connected
            and next_is_streaming == self._is_streaming
            and next_status == self._status
            and next_status_detail == self._status_detail
        ):
            return
        self._is_connected = next_is_connected
        self._is_streaming = next_is_streaming
        self._status = next_status
        self._status_detail = next_status_detail
