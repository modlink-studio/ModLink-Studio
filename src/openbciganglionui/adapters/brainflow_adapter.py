from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QObject

from ..backend import (
    BrainFlowGanglionBackend,
    ConnectConfig,
    DeviceSearchResult,
    DeviceState,
    ErrorEvent as LegacyErrorEvent,
    SearchEvent,
    StateEvent,
    StreamChunk,
)
from ..core.contracts import (
    AdapterCapabilities,
    ConnectionState,
    DeviceAdapter,
    DeviceConnectionConfig,
    DeviceDiscoveryResult,
    DeviceStatusEvent,
    DiscoveryEvent,
    DiscoveryQuery,
    ErrorEvent,
    FrameEnvelope,
    StreamCapabilities,
    StreamState,
    TimeseriesPayload,
)


class BrainFlowGanglionAdapter(DeviceAdapter):
    """Future-facing device adapter built on top of the deprecated legacy backend."""

    def __init__(
        self,
        legacy_backend: BrainFlowGanglionBackend | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self._legacy_backend = legacy_backend or BrainFlowGanglionBackend(parent=self)
        self._connection_state = ConnectionState.DISCONNECTED
        self._stream_state = StreamState.STOPPED
        self._capabilities = AdapterCapabilities(
            adapter_id=self.adapter_id,
            display_name=self.display_name,
            modalities=("eeg",),
            supports_discovery=True,
            supports_streaming=True,
            supports_device_marker=True,
            supported_transports=("Native BLE", "Ganglion Dongle"),
            stream_capabilities=(
                StreamCapabilities(
                    stream_id="brainflow:eeg",
                    modality="eeg",
                    payload_type="timeseries",
                    channel_count=4,
                    preferred_panels=("waveform",),
                ),
            ),
            metadata={"legacy_backend": "BrainFlowGanglionBackend"},
        )

        self._legacy_backend.sig_state.connect(self._on_legacy_state)
        self._legacy_backend.sig_stream.connect(self._on_legacy_stream)
        self._legacy_backend.sig_error.connect(self._on_legacy_error)
        self._legacy_backend.sig_search.connect(self._on_legacy_search)

    @property
    def adapter_id(self) -> str:
        return "brainflow_ganglion"

    @property
    def display_name(self) -> str:
        return "BrainFlow Ganglion"

    @property
    def connection_state(self) -> ConnectionState:
        return self._connection_state

    @property
    def stream_state(self) -> StreamState:
        return self._stream_state

    @property
    def capabilities(self) -> AdapterCapabilities:
        return self._capabilities

    @property
    def legacy_backend(self) -> BrainFlowGanglionBackend:
        return self._legacy_backend

    def discover(self, query: DiscoveryQuery | None = None) -> None:
        transport = (query.transport if query else "") or "Native BLE"
        self._legacy_backend.search_devices(transport)

    def connect(self, config: DeviceConnectionConfig | None = None) -> None:
        normalized = config or DeviceConnectionConfig()
        self._legacy_backend.connect_device(self._to_legacy_config(normalized))

    def disconnect(self) -> None:
        self._legacy_backend.disconnect_device()

    def start_stream(self) -> None:
        self._legacy_backend.start_preview()

    def stop_stream(self) -> None:
        self._legacy_backend.stop_preview()

    def _on_legacy_state(self, event: StateEvent) -> None:
        self._connection_state, self._stream_state = self._map_legacy_state(event.state)
        self.sig_status.emit(
            DeviceStatusEvent(
                adapter_id=self.adapter_id,
                display_name=self.display_name,
                connection_state=self._connection_state,
                stream_state=self._stream_state,
                ts=event.ts,
                device_name=event.device_name,
                device_address=event.device_address,
                message=event.message,
            )
        )

    def _on_legacy_stream(self, chunk: StreamChunk) -> None:
        self.sig_frame.emit(
            FrameEnvelope(
                stream_id="brainflow:eeg",
                modality="eeg",
                seq=chunk.seq,
                timestamp_ns=int(chunk.received_at * 1_000_000_000),
                clock_source="host_wall_time",
                payload_type="timeseries",
                payload=TimeseriesPayload(
                    samples=chunk.data,
                    sample_rate=chunk.fs,
                    channel_names=list(chunk.channel_names),
                    unit="uV",
                ),
                metadata={
                    "sample_index0": chunk.sample_index0,
                    "legacy_channel_names": tuple(chunk.channel_names),
                },
            )
        )

    def _on_legacy_error(self, event: LegacyErrorEvent) -> None:
        if self._connection_state == ConnectionState.CONNECTING:
            self._connection_state = ConnectionState.ERROR
        if self._stream_state in {
            StreamState.STARTING,
            StreamState.STREAMING,
            StreamState.STOPPING,
        }:
            self._stream_state = StreamState.ERROR

        self.sig_error.emit(
            ErrorEvent(
                code=event.code,
                message=event.message,
                ts=event.ts,
                detail=event.detail,
                recoverable=event.recoverable,
                origin="adapter",
            )
        )

    def _on_legacy_search(self, event: SearchEvent) -> None:
        self.sig_discovery.emit(
            DiscoveryEvent(
                adapter_id=self.adapter_id,
                transport=event.method,
                is_discovering=event.is_searching,
                ts=event.ts,
                results=tuple(
                    self._to_discovery_result(result) for result in event.results
                ),
                message=event.message,
            )
        )

    def _map_legacy_state(
        self, state: DeviceState
    ) -> tuple[ConnectionState, StreamState]:
        if state == DeviceState.CONNECTING:
            return ConnectionState.CONNECTING, StreamState.STOPPED
        if state == DeviceState.DISCONNECTING:
            return ConnectionState.DISCONNECTING, StreamState.STOPPING
        if state == DeviceState.CONNECTED:
            return ConnectionState.CONNECTED, StreamState.STOPPED
        if state in {DeviceState.PREVIEWING, DeviceState.RECORDING}:
            return ConnectionState.CONNECTED, StreamState.STREAMING
        if state == DeviceState.ERROR:
            return ConnectionState.ERROR, StreamState.ERROR
        return ConnectionState.DISCONNECTED, StreamState.STOPPED

    def _to_legacy_config(self, config: DeviceConnectionConfig) -> ConnectConfig:
        return ConnectConfig(
            fs=config.sample_rate,
            n_channels=config.n_channels,
            chunk_size=config.chunk_size,
            device_name=config.device_name,
            connection_method=config.transport,
            device_address=config.device_address,
            serial_port=config.serial_port,
            mac_address=config.mac_address,
            serial_number=config.serial_number,
            firmware_hint=config.firmware_hint,
            timeout_sec=config.timeout_sec,
            connect_delay_ms=config.connect_delay_ms,
        )

    def _to_discovery_result(self, result: DeviceSearchResult) -> DeviceDiscoveryResult:
        return DeviceDiscoveryResult(
            name=result.name,
            address=result.address,
            transport=result.method,
            serial_port=result.serial_port,
            mac_address=result.mac_address,
            serial_number=result.serial_number,
        )
