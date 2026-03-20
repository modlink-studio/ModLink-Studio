from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from packages.modlink_shared import FrameEnvelope, StreamDescriptor

from .utils import (
    SCHEMA_VERSION,
    descriptor_to_dict,
    format_recording_id,
    sanitize_path_component,
    write_json,
)
from .writers import BaseStreamRecordingWriter, create_stream_writer


class RecordingStorage:
    def __init__(
        self,
        root_dir: Path,
        *,
        session_name: str,
        recording_label: str | None,
        descriptor_snapshot: dict[str, StreamDescriptor],
        started_at_ns: int,
    ) -> None:
        self.root_dir = root_dir
        self.session_name = session_name
        self.recording_label = recording_label
        self.descriptor_snapshot = descriptor_snapshot
        self.started_at_ns = started_at_ns
        self.recording_id = format_recording_id(started_at_ns)
        self.session_dir_name = sanitize_path_component(
            session_name,
            fallback="session",
        )
        self.session_dir = self.root_dir / self.session_dir_name
        self.recording_dir = self.session_dir / "recordings" / self.recording_id
        self.annotations_dir = self.recording_dir / "annotations"
        self.streams_dir = self.recording_dir / "streams"
        self._frame_counts_by_stream: dict[str, int] = {
            stream_id: 0 for stream_id in descriptor_snapshot
        }
        self._stream_writers: dict[str, BaseStreamRecordingWriter] = {}

        self.root_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_session_manifest()
        self.annotations_dir.mkdir(parents=True, exist_ok=False)
        self.streams_dir.mkdir(parents=True, exist_ok=False)

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

        for descriptor in self.descriptor_snapshot.values():
            self._stream_writers[descriptor.stream_id] = create_stream_writer(
                self._stream_dir_for(descriptor),
                descriptor,
            )

        self._write_recording_manifest(stopped_at_ns=None, status="recording")

    @property
    def frame_counts_by_stream(self) -> dict[str, int]:
        return dict(self._frame_counts_by_stream)

    def append_frame(self, frame: FrameEnvelope) -> bool:
        writer = self._stream_writers.get(frame.stream_id)
        if writer is None:
            return False

        writer.append_frame(frame)
        self._frame_counts_by_stream[frame.stream_id] += 1
        return True

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

    def finalize(self, *, stopped_at_ns: int) -> None:
        for writer in self._stream_writers.values():
            writer.close()
        self._markers_file.close()
        self._segments_file.close()
        self._write_recording_manifest(
            stopped_at_ns=stopped_at_ns,
            status="completed",
        )

    def _ensure_session_manifest(self) -> None:
        self.session_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = self.session_dir / "session.json"
        if manifest_path.exists():
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            existing_name = payload.get("session_name")
            if existing_name != self.session_name:
                raise ValueError(
                    "session directory already exists with a different session_name"
                )
            return

        write_json(
            manifest_path,
            {
                "schema_version": SCHEMA_VERSION,
                "session_name": self.session_name,
                "session_dir_name": self.session_dir_name,
                "created_at_ns": self.started_at_ns,
            },
        )

    def _stream_dir_for(self, descriptor: StreamDescriptor) -> Path:
        modality_dir = sanitize_path_component(
            descriptor.modality or "unknown",
            fallback="unknown",
        )
        stream_name = sanitize_path_component(
            descriptor.stream_id,
            fallback="stream",
        )
        stream_hash = hashlib.sha1(
            descriptor.stream_id.encode("utf-8"),
            usedforsecurity=False,
        ).hexdigest()[:8]
        return self.streams_dir / modality_dir / f"{stream_name}-{stream_hash}"

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
                    for descriptor in self.descriptor_snapshot.values()
                ],
                "frame_counts_by_stream": self.frame_counts_by_stream,
            },
        )
