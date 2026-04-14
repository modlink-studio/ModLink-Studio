from __future__ import annotations

from pathlib import Path
from time import time_ns
from typing import Any

from modlink_sdk import FrameEnvelope, StreamDescriptor

from ._recording_support import (
    append_csv_row,
    descriptor_from_dict,
    descriptor_to_dict,
    next_frame_index,
    normalize_data_array,
    write_csv_header,
)
from .io import read_json, write_json, write_npz
from .layout import (
    generate_storage_id,
    recording_dir,
    recording_manifest_path,
    recordings_dir,
    safe_path_component,
    validate_storage_id,
)


class RecordingStore:
    def __init__(self, root_dir: Path) -> None:
        self.root_dir = Path(root_dir)

    def create_recording(
        self,
        recording_descriptors: dict[str, StreamDescriptor],
        *,
        recording_label: str | None = None,
        recording_id: str | None = None,
    ) -> str:
        if not isinstance(recording_descriptors, dict) or not all(
            isinstance(value, StreamDescriptor) for value in recording_descriptors.values()
        ):
            raise ValueError("recording_descriptors must be a dict[str, StreamDescriptor]")

        resolved_recording_id = (
            generate_storage_id("rec", time_ns())
            if recording_id is None
            else validate_storage_id(recording_id, "rec")
        )
        resolved_recording_dir = recording_dir(self.root_dir, resolved_recording_id)
        annotations_dir = resolved_recording_dir / "annotations"
        streams_dir = resolved_recording_dir / "streams"
        stream_ids: list[str] = []
        used_stream_dirs: set[str] = set()

        recordings_dir(self.root_dir).mkdir(parents=True, exist_ok=True)
        resolved_recording_dir.mkdir(parents=True, exist_ok=False)
        annotations_dir.mkdir(parents=True, exist_ok=False)
        streams_dir.mkdir(parents=True, exist_ok=False)
        write_csv_header(annotations_dir / "markers.csv", ["timestamp_ns", "label"])
        write_csv_header(annotations_dir / "segments.csv", ["start_ns", "end_ns", "label"])

        for descriptor in recording_descriptors.values():
            stream_dir_name = safe_path_component(descriptor.stream_id)
            if stream_dir_name in used_stream_dirs:
                raise ValueError(
                    f"stream directory collision for stream_id={descriptor.stream_id!r}"
                )
            used_stream_dirs.add(stream_dir_name)
            stream_ids.append(descriptor.stream_id)
            self._initialize_stream(streams_dir / stream_dir_name, descriptor)

        write_json(
            recording_manifest_path(self.root_dir, resolved_recording_id),
            {
                "recording_id": resolved_recording_id,
                "recording_label": recording_label,
                "stream_ids": stream_ids,
            },
        )
        return resolved_recording_id

    def append_frame(self, recording_id: str, frame: FrameEnvelope) -> None:
        if not isinstance(frame, FrameEnvelope):
            raise ValueError("append_frame expects a FrameEnvelope")

        stream_dir = self._stream_dir(recording_id, frame.stream_id)
        descriptor = self._stream_descriptor(recording_id, frame.stream_id)
        self._append_stream_frame(stream_dir, descriptor, frame)

    def add_marker(
        self,
        recording_id: str,
        timestamp_ns: int,
        label: str | None = None,
    ) -> None:
        append_csv_row(
            recording_dir(self.root_dir, recording_id) / "annotations" / "markers.csv",
            [int(timestamp_ns), "" if label is None else label],
        )

    def add_segment(
        self,
        recording_id: str,
        start_ns: int,
        end_ns: int,
        label: str | None = None,
    ) -> None:
        append_csv_row(
            recording_dir(self.root_dir, recording_id) / "annotations" / "segments.csv",
            [int(start_ns), int(end_ns), "" if label is None else label],
        )

    def _recording_manifest(self, recording_id: str) -> dict[str, Any]:
        return read_json(recording_manifest_path(self.root_dir, recording_id))

    def _stream_dir(self, recording_id: str, stream_id: str) -> Path:
        manifest = self._recording_manifest(recording_id)
        stream_ids = manifest.get("stream_ids", [])
        if not isinstance(stream_ids, list) or not all(isinstance(item, str) for item in stream_ids):
            raise ValueError(f"recording '{recording_id}' has invalid stream_ids payload")
        if stream_id not in stream_ids:
            raise KeyError(stream_id)
        return recording_dir(self.root_dir, recording_id) / "streams" / safe_path_component(
            stream_id
        )

    def _stream_descriptor(self, recording_id: str, stream_id: str) -> StreamDescriptor:
        stream_payload = read_json(self._stream_dir(recording_id, stream_id) / "stream.json")
        descriptor_payload = stream_payload.get("descriptor")
        if not isinstance(descriptor_payload, dict):
            raise ValueError(
                f"recording '{recording_id}' stream '{stream_id}' has invalid descriptor payload"
            )
        return descriptor_from_dict(descriptor_payload)

    def _initialize_stream(self, stream_dir: Path, descriptor: StreamDescriptor) -> None:
        stream_dir.mkdir(parents=True, exist_ok=False)
        frames_dir = stream_dir / "frames"
        frames_dir.mkdir(parents=True, exist_ok=False)
        write_json(
            stream_dir / "stream.json",
            {
                "stream_id": descriptor.stream_id,
                "descriptor": descriptor_to_dict(descriptor),
            },
        )
        write_csv_header(
            stream_dir / "frames.csv",
            ["frame_index", "timestamp_ns", "seq", "file_name"],
        )

    def _append_stream_frame(
        self,
        stream_dir: Path,
        descriptor: StreamDescriptor,
        frame: FrameEnvelope,
    ) -> None:
        if frame.stream_id != descriptor.stream_id:
            raise ValueError(
                f"unexpected stream_id '{frame.stream_id}' for descriptor '{descriptor.stream_id}'"
            )

        data = normalize_data_array(frame)
        frames_index_path = stream_dir / "frames.csv"
        frame_index = next_frame_index(frames_index_path)
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
