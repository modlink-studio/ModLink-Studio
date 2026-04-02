from __future__ import annotations

import csv
import re
from datetime import UTC, datetime
from pathlib import Path

from modlink_sdk import FrameEnvelope, StreamDescriptor

from .utils import (
    SCHEMA_VERSION,
    descriptor_to_dict,
    write_json,
)
from .writers import (
    BaseStreamRecordingWriter,
    create_stream_writer,
)


class AnnotationRecordingWriter:
    def __init__(self, annotations_dir: Path) -> None:
        self.annotations_dir = annotations_dir
        self.annotations_dir.mkdir(parents=True, exist_ok=True)

        self._markers_file = (self.annotations_dir / "markers.csv").open(
            "w",
            encoding="utf-8",
            newline="",
        )
        self._markers_writer = csv.writer(self._markers_file)
        self._markers_writer.writerow(["timestamp_ns", "label"])
        self._markers_file.flush()

        self._segments_file = (self.annotations_dir / "segments.csv").open(
            "w",
            encoding="utf-8",
            newline="",
        )
        self._segments_writer = csv.writer(self._segments_file)
        self._segments_writer.writerow(["start_ns", "end_ns", "label"])
        self._segments_file.flush()

    def add_marker(self, *, timestamp_ns: int, label: str | None) -> None:
        self._markers_writer.writerow(
            [int(timestamp_ns), "" if label is None else label]
        )
        self._markers_file.flush()

    def add_segment(self, *, start_ns: int, end_ns: int, label: str | None) -> None:
        self._segments_writer.writerow(
            [int(start_ns), int(end_ns), "" if label is None else label]
        )
        self._segments_file.flush()

    def close(self) -> None:
        self._markers_file.close()
        self._segments_file.close()


class RecordingStorage:
    def __init__(
        self,
        root_dir: Path,
        *,
        session_name: str,
        recording_label: str | None,
        recording_descriptors: dict[str, StreamDescriptor],
        started_at_ns: int,
    ) -> None:
        self.root_dir = root_dir
        self.session_name = session_name
        self.recording_label = recording_label
        self.recording_descriptors = recording_descriptors
        self.started_at_ns = started_at_ns
        timestamp = datetime.fromtimestamp(started_at_ns / 1_000_000_000, tz=UTC)
        self.recording_id = (
            f"{timestamp.strftime('%Y%m%dT%H%M%S')}_{started_at_ns % 1_000_000_000:09d}Z"
        )
        self.session_dir = self.root_dir / f"session_{session_name}"
        self.recording_dir = self.session_dir / self.recording_id
        self.annotations_dir = self.recording_dir / "annotations"
        self.streams_dir = self.recording_dir / "streams"
        self._frame_counts_by_stream: dict[str, int] = {
            stream_id: 0 for stream_id in recording_descriptors
        }
        self._stream_writers: dict[str, BaseStreamRecordingWriter] = {}

        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.recording_dir.mkdir(parents=True, exist_ok=False)
        self.annotations_dir.mkdir(parents=True, exist_ok=False)
        self.streams_dir.mkdir(parents=True, exist_ok=False)

        self._annotation_writer = AnnotationRecordingWriter(self.annotations_dir)

        for descriptor in self.recording_descriptors.values():
            self._stream_writers[descriptor.stream_id] = create_stream_writer(
                self._stream_dir_for(descriptor),
                descriptor,
            )

    @property
    def frame_counts_by_stream(self) -> dict[str, int]:
        return dict(self._frame_counts_by_stream)

    def append_frame(self, frame: FrameEnvelope) -> None:
        writer = self._stream_writers.get(frame.stream_id)
        if writer is None:
            raise ValueError(
                f"unexpected stream_id '{frame.stream_id}' outside recording descriptors"
            )

        writer.append_frame(frame)
        self._frame_counts_by_stream[frame.stream_id] += 1

    def add_marker(self, *, timestamp_ns: int, label: str | None) -> None:
        self._annotation_writer.add_marker(timestamp_ns=timestamp_ns, label=label)

    def add_segment(self, *, start_ns: int, end_ns: int, label: str | None) -> None:
        self._annotation_writer.add_segment(
            start_ns=start_ns,
            end_ns=end_ns,
            label=label,
        )

    def finalize(self, *, stopped_at_ns: int, status: str = "completed") -> None:
        first_error: Exception | None = None
        for writer in self._stream_writers.values():
            try:
                writer.close()
            except Exception as exc:
                if first_error is None:
                    first_error = exc
        try:
            self._annotation_writer.close()
        except Exception as exc:
            if first_error is None:
                first_error = exc
        try:
            self.write_manifest(stopped_at_ns=stopped_at_ns, status=status)
        except Exception as exc:
            if first_error is None:
                first_error = exc
        if first_error is not None:
            raise first_error

    def write_manifest(self, *, stopped_at_ns: int | None, status: str) -> None:
        self._write_recording_manifest(stopped_at_ns=stopped_at_ns, status=status)

    def _stream_dir_for(self, descriptor: StreamDescriptor) -> Path:
        device_dir = _safe_path_component(descriptor.device_id) or "unknown_device"
        modality_dir = _safe_path_component(descriptor.modality) or "unknown"
        return self.streams_dir / device_dir / modality_dir

    def _write_recording_manifest(
        self,
        *,
        stopped_at_ns: int | None,
        status: str,
    ) -> None:
        write_json(
            self.recording_dir / "recording.json",
            {
                "schema_version": SCHEMA_VERSION,
                "session_name": self.session_name,
                "recording_id": self.recording_id,
                "recording_label": self.recording_label,
                "started_at_ns": self.started_at_ns,
                "stopped_at_ns": stopped_at_ns,
                "status": status,
                "descriptor_snapshot": [
                    descriptor_to_dict(descriptor)
                    for descriptor in self.recording_descriptors.values()
                ],
                "frame_counts_by_stream": self.frame_counts_by_stream,
            },
        )


def _safe_path_component(value: str) -> str:
    normalized = re.sub(r'[<>:"/\\\\|?*]+', "_", str(value).strip())
    normalized = normalized.rstrip(". ")
    return normalized or "_"
