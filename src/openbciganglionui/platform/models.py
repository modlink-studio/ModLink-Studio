from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


@dataclass(slots=True)
class FrameEnvelope:
    stream_id: str
    timestamp_ns: int
    payload: object
    seq: int | None = None


@dataclass(slots=True)
class StreamDescriptor:
    stream_id: str
    modality: str
    payload_type: str
    display_name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class DeviceConnectionState(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    STREAMING = "streaming"
    ERROR = "error"


@dataclass(slots=True)
class DeviceStatusEvent:
    device_id: str
    state: DeviceConnectionState
    ts: float
    message: str = ""
    device_name: str = ""
    device_address: str = ""


@dataclass(slots=True)
class PlatformErrorEvent:
    code: str
    message: str
    ts: float
    origin: str
    detail: str = ""
    recoverable: bool = True
