from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

import numpy as np


class DeviceState(str, Enum):
    """Common runtime states shared by backend implementations."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    DISCONNECTING = "disconnecting"
    CONNECTED = "connected"
    PREVIEWING = "previewing"
    RECORDING = "recording"
    ERROR = "error"


@dataclass(slots=True)
class StateEvent:
    """Point-in-time snapshot of the backend runtime state.

    Semantics:
    - ``state`` is the new latest state after the transition has been applied.
    - ``message`` is display-oriented and not intended for branching logic.
    - ``device_name`` and ``device_address`` should reflect the latest known
      identity information at the time of emission.
    """

    state: DeviceState
    ts: float
    message: str = ""
    device_name: str = "Ganglion Mock"
    device_address: str = ""


@dataclass(slots=True)
class StreamChunk:
    """One contiguous chunk of stream samples.

    Contract:
    - ``data`` has shape ``(n_samples, n_channels)``.
    - ``channel_names`` length must equal ``data.shape[1]``.
    - ``sample_index0`` is the absolute sample index of ``data[0]`` within the
      current streaming epoch.
    - Consumers should not invent their own x-axis. Use
      ``sample_index0 + arange(n_samples)``.
    - Implementations should usually emit monotonically increasing chunks within
      one streaming epoch, but consumers must tolerate forward gaps and backward
      resets across reconnect/restart boundaries.
    """

    seq: int
    sample_index0: int
    fs: float
    channel_names: tuple[str, ...]
    data: np.ndarray
    received_at: float


@dataclass(slots=True)
class MarkerEvent:
    """Marker inserted into the active live stream and/or recording session."""

    marker_id: str
    label: str
    wall_time: float
    sample_index: int
    note: str = ""
    source: str = "ui"


@dataclass(slots=True)
class RecordEvent:
    """Recording state transition event.

    ``is_recording`` is the accepted new recording state after the operation.
    ``sample_index`` is the backend's best-known stream anchor for the
    transition moment when available.
    """

    is_recording: bool
    ts: float
    session_id: Optional[str] = None
    save_dir: Optional[str] = None
    sample_index: Optional[int] = None


@dataclass(slots=True)
class ErrorEvent:
    """Recoverable or terminal backend error surfaced to the UI."""

    code: str
    message: str
    ts: float
    detail: str = ""
    recoverable: bool = True


@dataclass(slots=True)
class ConnectConfig:
    """Connection and stream-shape configuration for a connection attempt."""

    fs: float = 200.0
    n_channels: int = 4
    chunk_size: int = 10
    device_name: str = "Ganglion Mock"
    connection_method: str = "Native BLE"
    device_address: str = ""
    connect_delay_ms: int = 500


@dataclass(slots=True)
class RecordSession:
    """Recording session metadata supplied by the UI or backend."""

    session_id: str
    save_dir: str
    subject_id: str = "S01"
    task_name: str = "swallow_experiment"
    operator: str = ""
    notes: str = ""


@dataclass(slots=True)
class DeviceSearchResult:
    """A connectable device candidate discovered by a search operation."""

    name: str
    address: str
    method: str


@dataclass(slots=True)
class SearchEvent:
    """Search progress/result event for device discovery."""

    method: str
    is_searching: bool
    ts: float
    results: tuple[DeviceSearchResult, ...] = ()
    message: str = ""


@dataclass(slots=True)
class LabelsEvent:
    """Latest full label snapshot after a label-related operation."""

    labels: tuple[str, ...]
    ts: float
    storage_path: str = ""
    message: str = ""


@dataclass(slots=True)
class SaveDirEvent:
    """Latest default save directory snapshot after a save-dir operation."""

    save_dir: str
    ts: float
    message: str = ""
