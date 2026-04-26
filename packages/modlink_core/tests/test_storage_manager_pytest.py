from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

from modlink_core.storage import (
    add_recording_marker,
    add_recording_segment,
    add_recording_to_session,
    add_session_to_experiment,
    append_recording_frame,
    create_experiment,
    create_recording,
    create_session,
    list_experiments,
    list_sessions,
    read_experiment,
    read_session,
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


def test_session_store_creates_initial_manifest_and_adds_recordings(tmp_path) -> None:
    session_id = create_session(
        tmp_path,
        session_id="ses_demo",
        display_name="demo session",
        metadata={"operator": "alice"},
        created_at_ns=123,
    )
    add_recording_to_session(tmp_path, session_id, "rec_a", updated_at_ns=456)
    add_recording_to_session(tmp_path, session_id, "rec_b", updated_at_ns=789)
    add_recording_to_session(tmp_path, session_id, "rec_b", updated_at_ns=999)

    assert session_id == "ses_demo"
    payload = json.loads(
        (tmp_path / "sessions" / session_id / "session.json").read_text(encoding="utf-8")
    )
    assert payload == {
        "schema_version": 1,
        "session_id": "ses_demo",
        "display_name": "demo session",
        "created_at_ns": 123,
        "updated_at_ns": 999,
        "recording_ids": ["rec_a", "rec_b"],
        "metadata": {"operator": "alice"},
    }
    assert read_session(tmp_path, session_id) == payload
    assert list_sessions(tmp_path) == [payload]


def test_experiment_store_creates_initial_manifest_and_adds_sessions(tmp_path) -> None:
    experiment_id = create_experiment(
        tmp_path,
        experiment_id="exp_demo",
        display_name="demo experiment",
        metadata={"study": "visual"},
        created_at_ns=321,
    )
    add_session_to_experiment(tmp_path, experiment_id, "ses_a", updated_at_ns=654)
    add_session_to_experiment(tmp_path, experiment_id, "ses_b", updated_at_ns=987)
    add_session_to_experiment(tmp_path, experiment_id, "ses_b", updated_at_ns=1_111)

    assert experiment_id == "exp_demo"
    payload = json.loads(
        (tmp_path / "experiments" / experiment_id / "experiment.json").read_text(encoding="utf-8")
    )
    assert payload == {
        "schema_version": 1,
        "experiment_id": "exp_demo",
        "display_name": "demo experiment",
        "created_at_ns": 321,
        "updated_at_ns": 1_111,
        "session_ids": ["ses_a", "ses_b"],
        "metadata": {"study": "visual"},
    }
    assert read_experiment(tmp_path, experiment_id) == payload
    assert list_experiments(tmp_path) == [payload]


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))
