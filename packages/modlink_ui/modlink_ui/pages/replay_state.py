from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from modlink_core.models import (
    ExportJobSnapshot,
    ReplayMarker,
    ReplayRecordingSummary,
    ReplaySegment,
    ReplaySnapshot,
)

EXPORT_LABELS = {
    "signal_csv": "Signal CSV",
    "signal_npz": "Signal NPZ",
    "raster_npz": "Raster NPZ",
    "field_npz": "Field NPZ",
    "video_frames_zip": "Video Frames ZIP",
    "recording_bundle_zip": "Recording Bundle ZIP",
}


@dataclass(frozen=True, slots=True)
class ReplayStatusViewState:
    status_text: str
    hint_text: str
    playback_progress_value: int
    playback_progress_text: str
    can_play: bool
    can_pause: bool
    can_stop: bool
    can_export: bool


@dataclass(frozen=True, slots=True)
class ReplayExportProgressViewState:
    value: int
    text: str


@dataclass(frozen=True, slots=True)
class ReplayAnnotationSelection:
    marker_index: int = -1
    segment_index: int = -1


def build_recording_item_text(summary: ReplayRecordingSummary) -> str:
    title = summary.recording_label or summary.recording_id
    subtitle = f"{summary.recording_id} · {len(summary.stream_ids)} streams"
    return f"{title}\n{subtitle}"


def build_marker_item_text(marker: ReplayMarker) -> str:
    return f"{format_time_ns(marker.timestamp_ns)} · {marker.label or '未命名'}"


def build_segment_item_text(segment: ReplaySegment) -> str:
    return (
        f"{format_time_ns(segment.start_ns)} → {format_time_ns(segment.end_ns)}"
        f" · {segment.label or '未命名'}"
    )


def build_export_job_item_text(job: ExportJobSnapshot) -> str:
    output_text = "" if not job.output_path else f" · {job.output_path}"
    error_text = "" if not job.error else f" · {job.error}"
    return (
        f"{EXPORT_LABELS.get(job.format_id, job.format_id)}"
        f" · {job.state} · {int(job.progress * 100)}%"
        f"{output_text}{error_text}"
    )


def build_replay_status_view_state(
    snapshot: ReplaySnapshot,
    *,
    export_root_dir: Path,
) -> ReplayStatusViewState:
    duration_ns = max(0, snapshot.duration_ns)
    position_ns = min(max(0, snapshot.position_ns), duration_ns)
    progress_value = 0 if duration_ns == 0 else int(round(position_ns / duration_ns * 1000))
    recording_id = snapshot.recording_id or "未打开"
    return ReplayStatusViewState(
        status_text=(
            f"状态：{snapshot.state} · recording：{recording_id}"
            f" · 位置：{format_time_ns(snapshot.position_ns)} / {format_time_ns(snapshot.duration_ns)}"
        ),
        hint_text=f"导出根目录：{export_root_dir}",
        playback_progress_value=progress_value,
        playback_progress_text=f"{format_time_ns(position_ns)} / {format_time_ns(duration_ns)}",
        can_play=snapshot.recording_id is not None and snapshot.state != "playing",
        can_pause=snapshot.state == "playing",
        can_stop=snapshot.recording_id is not None and snapshot.state != "idle",
        can_export=snapshot.recording_id is not None,
    )


def build_export_progress_view_state(
    jobs: Sequence[ExportJobSnapshot],
) -> ReplayExportProgressViewState:
    if not jobs:
        return ReplayExportProgressViewState(value=0, text="尚未开始导出")

    latest_job = jobs[-1]
    return ReplayExportProgressViewState(
        value=int(round(float(latest_job.progress) * 1000)),
        text=(
            f"{EXPORT_LABELS.get(latest_job.format_id, latest_job.format_id)}"
            f" · {latest_job.state} · {int(latest_job.progress * 100)}%"
        ),
    )


def find_annotation_selection(
    snapshot: ReplaySnapshot,
    *,
    markers: Sequence[ReplayMarker],
    segments: Sequence[ReplaySegment],
) -> ReplayAnnotationSelection:
    current_position_ns = snapshot.position_ns

    active_marker_index = -1
    for index, marker in enumerate(markers):
        if marker.timestamp_ns <= current_position_ns:
            active_marker_index = index

    active_segment_index = -1
    for index, segment in enumerate(segments):
        if segment.start_ns <= current_position_ns <= segment.end_ns:
            active_segment_index = index
            break

    return ReplayAnnotationSelection(
        marker_index=active_marker_index,
        segment_index=active_segment_index,
    )


def format_time_ns(value: int) -> str:
    total_ms = max(0, int(value // 1_000_000))
    total_seconds, millis = divmod(total_ms, 1000)
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"
    return f"{minutes:02d}:{seconds:02d}.{millis:03d}"
