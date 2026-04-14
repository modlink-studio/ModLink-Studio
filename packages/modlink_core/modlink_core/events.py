from __future__ import annotations

from typing import Any, Literal

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DriverConnectionLostEvent:
    driver_id: str
    detail: object | None = None
    kind: Literal["driver_connection_lost"] = "driver_connection_lost"


@dataclass(frozen=True, slots=True)
class DriverExecutorFailedEvent:
    driver_id: str
    detail: object
    kind: Literal["driver_executor_failed"] = "driver_executor_failed"


@dataclass(frozen=True, slots=True)
class RecordingFailedEvent:
    recording_id: str
    recording_path: str
    frame_counts_by_stream: dict[str, int]
    reason: str
    ts_ns: int
    kind: Literal["recording_failed"] = "recording_failed"


@dataclass(frozen=True, slots=True)
class SettingChangedEvent:
    key: str
    value: Any
    ts: float
    kind: Literal["setting_changed"] = "setting_changed"


type BackendEvent = (
    DriverConnectionLostEvent
    | DriverExecutorFailedEvent
    | RecordingFailedEvent
    | SettingChangedEvent
)
