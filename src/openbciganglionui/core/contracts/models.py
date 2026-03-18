from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ConnectionState(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    ERROR = "error"


class StreamState(str, Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    STREAMING = "streaming"
    STOPPING = "stopping"
    ERROR = "error"


class RecordingMode(str, Enum):
    CLIP = "clip"
    CONTINUOUS = "continuous"


class SessionState(str, Enum):
    IDLE = "idle"
    STARTING = "starting"
    ACTIVE = "active"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass(slots=True)
class DeviceConnectionConfig:
    sample_rate: float = 200.0
    n_channels: int = 4
    chunk_size: int = 10
    device_name: str = "Ganglion"
    transport: str = "Native BLE"
    device_address: str = ""
    serial_port: str = ""
    mac_address: str = ""
    serial_number: str = ""
    firmware_hint: str = "auto"
    timeout_sec: int = 15
    connect_delay_ms: int = 500


@dataclass(slots=True)
class DiscoveryQuery:
    transport: str = ""
    timeout_sec: float = 5.0


@dataclass(slots=True)
class DeviceDiscoveryResult:
    name: str
    address: str
    transport: str
    serial_port: str = ""
    mac_address: str = ""
    serial_number: str = ""


@dataclass(slots=True)
class StreamCapabilities:
    stream_id: str
    modality: str
    payload_type: str
    channel_count: int = 0
    preferred_panels: tuple[str, ...] = ()


@dataclass(slots=True)
class AdapterCapabilities:
    adapter_id: str
    display_name: str
    modalities: tuple[str, ...]
    supports_discovery: bool
    supports_streaming: bool
    supports_device_marker: bool
    supported_transports: tuple[str, ...]
    stream_capabilities: tuple[StreamCapabilities, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DeviceStatusEvent:
    adapter_id: str
    display_name: str
    connection_state: ConnectionState
    stream_state: StreamState
    ts: float
    device_name: str = ""
    device_address: str = ""
    message: str = ""


@dataclass(slots=True)
class DiscoveryEvent:
    adapter_id: str
    transport: str
    is_discovering: bool
    ts: float
    results: tuple[DeviceDiscoveryResult, ...] = ()
    message: str = ""


@dataclass(slots=True)
class ErrorEvent:
    code: str
    message: str
    ts: float
    detail: str = ""
    recoverable: bool = True
    origin: str = ""


@dataclass(slots=True)
class TimeseriesPayload:
    samples: Any
    sample_rate: float
    channel_names: list[str]
    unit: str | None = None


@dataclass(slots=True)
class EventPayload:
    name: str
    value: Any = None
    description: str = ""


@dataclass(slots=True)
class FrameEnvelope:
    stream_id: str
    modality: str
    seq: int
    timestamp_ns: int
    clock_source: str
    payload_type: str
    payload: TimeseriesPayload | EventPayload
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SessionPlan:
    session_id: str
    save_dir: str
    subject_id: str
    task_name: str
    recording_mode: RecordingMode = RecordingMode.CLIP
    operator: str = ""
    notes: str = ""


@dataclass(slots=True)
class SessionEvent:
    state: SessionState
    ts: float
    session_id: str = ""
    message: str = ""


@dataclass(slots=True)
class RecordingEvent:
    is_recording: bool
    ts: float
    session_id: str = ""
    save_dir: str = ""
    recording_mode: RecordingMode = RecordingMode.CLIP


@dataclass(slots=True)
class MarkerEvent:
    marker_id: str
    label: str
    timestamp_ns: int
    note: str = ""
    source: str = "ui"


@dataclass(slots=True)
class SegmentEvent:
    action: str
    segment_id: str
    label: str
    ts: float
    start_sample_index: int
    end_sample_index: int | None = None
    session_id: str = ""
    note: str = ""
    source: str = "ui"
