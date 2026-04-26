from __future__ import annotations

from pathlib import Path
from time import time_ns
from typing import Any

import numpy as np

from modlink_sdk import FrameEnvelope, StreamDescriptor

from ._internal.files import (
    append_csv_row,
    read_csv_rows,
    read_json,
    write_csv_header,
    write_json,
    write_npz,
)
from ._internal.ids import (
    generate_storage_id,
    safe_path_component,
    validate_storage_id,
)


def create_recording(
    root_dir: Path,
    recording_descriptors: dict[str, StreamDescriptor],
    *,
    recording_label: str | None = None,
    recording_id: str | None = None,
) -> str:
    root_dir = Path(root_dir)
    if not isinstance(recording_descriptors, dict) or not all(
        isinstance(value, StreamDescriptor) for value in recording_descriptors.values()
    ):
        raise ValueError("recording_descriptors must be a dict[str, StreamDescriptor]")

    resolved_recording_id = (
        generate_storage_id("rec", time_ns())
        if recording_id is None
        else validate_storage_id(recording_id, "rec")
    )
    resolved_recording_dir = root_dir / "recordings" / resolved_recording_id
    annotations_dir = resolved_recording_dir / "annotations"
    streams_dir = resolved_recording_dir / "streams"
    stream_ids: list[str] = []
    used_stream_dirs: set[str] = set()

    (root_dir / "recordings").mkdir(parents=True, exist_ok=True)
    resolved_recording_dir.mkdir(parents=True, exist_ok=False)
    annotations_dir.mkdir(parents=True, exist_ok=False)
    streams_dir.mkdir(parents=True, exist_ok=False)
    write_csv_header(annotations_dir / "markers.csv", ["timestamp_ns", "label"])
    write_csv_header(annotations_dir / "segments.csv", ["start_ns", "end_ns", "label"])

    for descriptor in recording_descriptors.values():
        stream_dir_name = safe_path_component(descriptor.stream_id)
        if stream_dir_name in used_stream_dirs:
            raise ValueError(f"stream directory collision for stream_id={descriptor.stream_id!r}")
        used_stream_dirs.add(stream_dir_name)
        stream_ids.append(descriptor.stream_id)
        _initialize_stream(streams_dir / stream_dir_name, descriptor)

    write_json(
        resolved_recording_dir / "recording.json",
        {
            "recording_id": resolved_recording_id,
            "recording_label": recording_label,
            "stream_ids": stream_ids,
        },
    )
    return resolved_recording_id


def append_recording_frame(root_dir: Path, recording_id: str, frame: FrameEnvelope) -> None:
    if not isinstance(frame, FrameEnvelope):
        raise ValueError("append_recording_frame expects a FrameEnvelope")
    _append_stream_frame(_stream_dir(root_dir, recording_id, frame.stream_id), frame)


def add_recording_marker(
    root_dir: Path,
    recording_id: str,
    timestamp_ns: int,
    label: str | None = None,
) -> None:
    root_dir = Path(root_dir)
    append_csv_row(
        root_dir / "recordings" / recording_id / "annotations" / "markers.csv",
        [int(timestamp_ns), "" if label is None else label],
    )


def add_recording_segment(
    root_dir: Path,
    recording_id: str,
    start_ns: int,
    end_ns: int,
    label: str | None = None,
) -> None:
    root_dir = Path(root_dir)
    append_csv_row(
        root_dir / "recordings" / recording_id / "annotations" / "segments.csv",
        [int(start_ns), int(end_ns), "" if label is None else label],
    )


def list_recordings(root_dir: Path) -> list[dict[str, Any]]:
    base_dir = Path(root_dir) / "recordings"
    if not base_dir.is_dir():
        return []

    manifests: list[dict[str, Any]] = []
    for entry in sorted(base_dir.iterdir(), key=lambda item: item.name, reverse=True):
        manifest_path = entry / "recording.json"
        if not manifest_path.is_file():
            continue
        try:
            manifests.append(read_json(manifest_path))
        except Exception:
            continue
    return manifests


def read_recording(root_dir: Path, recording_id: str) -> dict[str, Any]:
    return read_json(_recording_dir(root_dir, recording_id) / "recording.json")


def read_recording_stream(root_dir: Path, recording_id: str, stream_id: str) -> dict[str, Any]:
    return read_json(_stream_dir(root_dir, recording_id, stream_id) / "stream.json")


def read_recording_markers(root_dir: Path, recording_id: str) -> list[dict[str, str]]:
    markers_path = _recording_dir(root_dir, recording_id) / "annotations" / "markers.csv"
    if not markers_path.is_file():
        return []
    return read_csv_rows(markers_path)


def read_recording_segments(root_dir: Path, recording_id: str) -> list[dict[str, str]]:
    segments_path = _recording_dir(root_dir, recording_id) / "annotations" / "segments.csv"
    if not segments_path.is_file():
        return []
    return read_csv_rows(segments_path)


def read_recording_frames(
    root_dir: Path, recording_id: str, stream_id: str
) -> list[dict[str, str]]:
    return read_csv_rows(_stream_dir(root_dir, recording_id, stream_id) / "frames.csv")


def load_recording_frame_data(
    root_dir: Path,
    recording_id: str,
    stream_id: str,
    file_name: str,
) -> np.ndarray:
    frame_path = _stream_dir(root_dir, recording_id, stream_id) / "frames" / str(file_name)
    if not frame_path.is_file():
        raise FileNotFoundError(frame_path)

    with np.load(frame_path) as archive:
        if "data" not in archive.files:
            raise ValueError(f"recording frame '{frame_path}' is missing data payload")
        return np.ascontiguousarray(archive["data"])


def _recording_dir(root_dir: Path, recording_id: str) -> Path:
    recording_dir = Path(root_dir) / "recordings" / str(recording_id)
    if not (recording_dir / "recording.json").is_file():
        raise FileNotFoundError(recording_dir / "recording.json")
    return recording_dir


def _stream_dir(root_dir: Path, recording_id: str, stream_id: str) -> Path:
    root_dir = Path(root_dir)
    stream_dir = _recording_dir(root_dir, recording_id) / "streams" / safe_path_component(stream_id)
    if not (stream_dir / "stream.json").is_file():
        raise KeyError(stream_id)
    return stream_dir


def _initialize_stream(stream_dir: Path, descriptor: StreamDescriptor) -> None:
    stream_dir.mkdir(parents=True, exist_ok=False)
    frames_dir = stream_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=False)
    write_json(
        stream_dir / "stream.json",
        {
            "stream_id": descriptor.stream_id,
            "descriptor": _descriptor_to_dict(descriptor),
        },
    )
    write_csv_header(
        stream_dir / "frames.csv",
        ["frame_index", "timestamp_ns", "seq", "file_name"],
    )


def _append_stream_frame(stream_dir: Path, frame: FrameEnvelope) -> None:
    data = _normalize_data_array(frame)
    frames_index_path = stream_dir / "frames.csv"
    frame_index = len(read_csv_rows(frames_index_path)) + 1
    file_name = f"{frame_index:06d}.npz"
    write_npz(stream_dir / "frames" / file_name, data=data)
    append_csv_row(
        frames_index_path,
        [
            frame_index,
            int(frame.timestamp_ns),
            "" if frame.seq is None else int(frame.seq),
            file_name,
        ],
    )


def _descriptor_to_dict(descriptor: StreamDescriptor) -> dict[str, Any]:
    return {
        "device_id": descriptor.device_id,
        "stream_id": descriptor.stream_id,
        "stream_key": descriptor.stream_key,
        "payload_type": descriptor.payload_type,
        "nominal_sample_rate_hz": descriptor.nominal_sample_rate_hz,
        "chunk_size": descriptor.chunk_size,
        "channel_names": list(descriptor.channel_names),
        "display_name": descriptor.display_name,
        "metadata": dict(descriptor.metadata),
    }


def _normalize_data_array(frame: FrameEnvelope) -> np.ndarray:
    data = np.asarray(frame.data)
    if data.dtype == np.dtype("O"):
        raise ValueError(f"stream_id={frame.stream_id}: object dtype arrays are not supported")
    return np.ascontiguousarray(data)
