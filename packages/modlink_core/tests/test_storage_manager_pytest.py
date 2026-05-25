from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

from modlink_core.storage import (
    add_recording_marker,
    add_recording_segment,
    append_recording_frame,
    create_recording,
)


def test_recording_storage_writes_minimal_recording_layout(
    tmp_path,
    descriptor_factory,
    frame_factory,
) -> None:
    descriptor = descriptor_factory(payload_type="signal", chunk_size=3, channel_names=("f3", "f4"))
    recording_id = create_recording(
        tmp_path,
        {descriptor.stream_id: descriptor},
        recording_label="baseline",
    )
    append_recording_frame(
        tmp_path,
        recording_id,
        frame_factory(descriptor, timestamp_ns=1_700_000_000_123_456_789, seq=1),
        frame_index=1,
    )

    recording_root = tmp_path / "recordings" / recording_id
    stream_root = recording_root / "streams" / "demo.01_demo"
    manifest = json.loads((recording_root / "recording.json").read_text(encoding="utf-8"))
    stream_manifest = json.loads((stream_root / "stream.json").read_text(encoding="utf-8"))
    frame_rows = _read_csv_rows(stream_root / "frames.csv")

    assert recording_id.startswith("rec_")
    assert manifest == {
        "recording_id": recording_id,
        "recording_label": "baseline",
        "session_name": None,
        "experiment_name": None,
        "stream_ids": [descriptor.stream_id],
    }
    assert stream_manifest == {
        "stream_id": descriptor.stream_id,
        "descriptor": {
            "device_id": descriptor.device_id,
            "stream_id": descriptor.stream_id,
            "stream_key": descriptor.stream_key,
            "payload_type": descriptor.payload_type,
            "nominal_sample_rate_hz": descriptor.nominal_sample_rate_hz,
            "chunk_size": descriptor.chunk_size,
            "channel_names": list(descriptor.channel_names),
            "display_name": descriptor.display_name,
            "metadata": dict(descriptor.metadata),
        },
    }
    assert frame_rows == [
        {
            "frame_index": "1",
            "timestamp_ns": "1700000000123456789",
            "seq": "1",
            "file_name": "000001.npz",
        }
    ]
    with np.load(stream_root / "frames" / "000001.npz") as archive:
        assert set(archive.files) == {"data"}


def test_recording_storage_persists_session_and_experiment_labels(
    tmp_path,
    descriptor_factory,
) -> None:
    descriptor = descriptor_factory(payload_type="signal", chunk_size=2)
    recording_id = create_recording(
        tmp_path,
        {descriptor.stream_id: descriptor},
        recording_label="trial_03",
        session_name="healthy_H03",
        experiment_name="吞咽采集_2026Q2",
    )

    manifest = json.loads(
        (tmp_path / "recordings" / recording_id / "recording.json").read_text(encoding="utf-8")
    )
    assert manifest["session_name"] == "healthy_H03"
    assert manifest["experiment_name"] == "吞咽采集_2026Q2"
    assert manifest["recording_label"] == "trial_03"


def test_recording_storage_normalizes_blank_label_strings(
    tmp_path,
    descriptor_factory,
) -> None:
    descriptor = descriptor_factory(payload_type="signal", chunk_size=2)
    recording_id = create_recording(
        tmp_path,
        {descriptor.stream_id: descriptor},
        session_name="   ",
        experiment_name="",
    )

    manifest = json.loads(
        (tmp_path / "recordings" / recording_id / "recording.json").read_text(encoding="utf-8")
    )
    assert manifest["session_name"] is None
    assert manifest["experiment_name"] is None


def test_recording_storage_writes_annotations_without_readback_api(
    tmp_path,
    descriptor_factory,
    frame_factory,
) -> None:
    descriptor = descriptor_factory(payload_type="field", chunk_size=2)
    recording_id = create_recording(
        tmp_path,
        {descriptor.stream_id: descriptor},
        recording_label="replay_case",
    )

    append_recording_frame(
        tmp_path,
        recording_id,
        frame_factory(
            descriptor,
            timestamp_ns=1_700_000_000_500_000_000,
            seq=17,
            channel_count=2,
            height=3,
            width=4,
        ),
        frame_index=1,
    )
    add_recording_marker(tmp_path, recording_id, 1_700_000_000_500_000_123, "start")
    add_recording_segment(
        tmp_path,
        recording_id,
        1_700_000_000_500_000_123,
        1_700_000_000_600_000_123,
        "segment_a",
    )

    recording_root = tmp_path / "recordings" / recording_id
    assert _read_csv_rows(recording_root / "annotations" / "markers.csv") == [
        {"timestamp_ns": "1700000000500000123", "label": "start"}
    ]
    assert _read_csv_rows(recording_root / "annotations" / "segments.csv") == [
        {
            "start_ns": "1700000000500000123",
            "end_ns": "1700000000600000123",
            "label": "segment_a",
        }
    ]


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))
