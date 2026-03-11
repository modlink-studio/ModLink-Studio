from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

import numpy as np


class DeviceState(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    DISCONNECTING = "disconnecting"
    CONNECTED = "connected"
    PREVIEWING = "previewing"
    RECORDING = "recording"
    ERROR = "error"


@dataclass(slots=True)
class StateEvent:
    state: DeviceState
    ts: float
    message: str = ""
    device_name: str = "Ganglion Mock"
    device_address: str = ""


@dataclass(slots=True)
class StreamChunk:
    seq: int
    sample_index0: int
    fs: float
    channel_names: tuple[str, ...]
    data: np.ndarray
    received_at: float


@dataclass(slots=True)
class MarkerEvent:
    marker_id: str
    label: str
    wall_time: float
    sample_index: int
    note: str = ""
    source: str = "ui"


@dataclass(slots=True)
class RecordEvent:
    is_recording: bool
    ts: float
    session_id: Optional[str] = None
    save_dir: Optional[str] = None


@dataclass(slots=True)
class ErrorEvent:
    code: str
    message: str
    ts: float
    detail: str = ""
    recoverable: bool = True


@dataclass(slots=True)
class ConnectConfig:
    fs: float = 200.0
    n_channels: int = 4
    chunk_size: int = 10
    device_name: str = "Ganglion Mock"
    connection_method: str = "Native BLE"
    device_address: str = ""
    connect_delay_ms: int = 500


@dataclass(slots=True)
class RecordSession:
    session_id: str
    save_dir: str
    subject_id: str = "S01"
    task_name: str = "swallow_experiment"
    operator: str = ""
    notes: str = ""


@dataclass(slots=True)
class DeviceSearchResult:
    name: str
    address: str
    method: str


@dataclass(slots=True)
class SearchEvent:
    method: str
    is_searching: bool
    ts: float
    results: tuple[DeviceSearchResult, ...] = ()
    message: str = ""


@dataclass(slots=True)
class LabelsEvent:
    labels: tuple[str, ...]
    ts: float
    storage_path: str = ""
    message: str = ""
