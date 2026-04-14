from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DriverSnapshot:
    driver_id: str
    display_name: str
    supported_providers: tuple[str, ...]
    is_running: bool
    is_connected: bool
    is_streaming: bool


@dataclass(frozen=True, slots=True)
class RecordingSnapshot:
    state: str
    is_started: bool
    is_recording: bool
    root_dir: str


@dataclass(frozen=True, slots=True)
class RecordingStartSummary:
    recording_id: str
    recording_path: str
    started_at_ns: int


@dataclass(frozen=True, slots=True)
class RecordingStopSummary:
    recording_id: str
    recording_path: str
    started_at_ns: int
    stopped_at_ns: int
    status: str
    frame_counts_by_stream: dict[str, int]
