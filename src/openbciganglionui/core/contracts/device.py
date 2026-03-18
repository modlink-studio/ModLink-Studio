from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal

from .models import (
    AdapterCapabilities,
    DeviceConnectionConfig,
    ConnectionState,
    DiscoveryQuery,
    StreamState,
)


class DeviceAdapter(QObject):
    """Stable device-facing runtime port for future platform integrations."""

    sig_status = pyqtSignal(object)
    sig_frame = pyqtSignal(object)
    sig_error = pyqtSignal(object)
    sig_discovery = pyqtSignal(object)

    def _not_implemented(self, member: str) -> None:
        raise NotImplementedError(
            f"{type(self).__name__} must implement DeviceAdapter.{member}"
        )

    @property
    def adapter_id(self) -> str:
        self._not_implemented("adapter_id")

    @property
    def display_name(self) -> str:
        self._not_implemented("display_name")

    @property
    def connection_state(self) -> ConnectionState:
        self._not_implemented("connection_state")

    @property
    def stream_state(self) -> StreamState:
        self._not_implemented("stream_state")

    @property
    def capabilities(self) -> AdapterCapabilities:
        self._not_implemented("capabilities")

    def discover(self, query: DiscoveryQuery | None = None) -> None:
        self._not_implemented("discover")

    def connect(self, config: DeviceConnectionConfig | None = None) -> None:
        self._not_implemented("connect")

    def disconnect(self) -> None:
        self._not_implemented("disconnect")

    def start_stream(self) -> None:
        self._not_implemented("start_stream")

    def stop_stream(self) -> None:
        self._not_implemented("stop_stream")

    def get_capabilities(self) -> AdapterCapabilities:
        return self.capabilities
