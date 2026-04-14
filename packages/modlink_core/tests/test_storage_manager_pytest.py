from __future__ import annotations

import json

from modlink_core.storage import ExperimentStore, RecordingStore, SessionStore


def test_recording_storage_writes_new_recording_root_layout(
    tmp_path,
    descriptor_factory,
    frame_factory,
) -> None:
    descriptor = descriptor_factory(payload_type="signal", chunk_size=3, channel_names=("f3", "f4"))
    storage = RecordingStore(tmp_path)
    writer = storage.open_writer(
        {descriptor.stream_id: descriptor},
        recording_label="baseline",
        started_at_ns=1_700_000_000_123_456_789,
    )

    start_summary = writer.start_summary()
    writer.append_frame(frame_factory(descriptor, timestamp_ns=1_700_000_000_123_456_789, seq=1))
    stop_summary = writer.finalize(stopped_at_ns=1_700_000_001_123_456_789, status="completed")

    assert start_summary.recording_id.startswith("rec_")
    assert stop_summary.recording_id == start_summary.recording_id
    assert writer.recording_dir == tmp_path / "recordings" / start_summary.recording_id

    manifest = json.loads((writer.recording_dir / "recording.json").read_text(encoding="utf-8"))
    assert manifest["recording_id"] == start_summary.recording_id
    assert manifest["recording_label"] == "baseline"
    assert manifest["status"] == "completed"
    assert manifest["streams"] == [
        {
            "stream_id": descriptor.stream_id,
            "path": "streams/demo.01_demo",
        }
    ]
    assert (writer.recording_dir / "streams" / "demo.01_demo" / "stream.json").is_file()


def test_session_store_creates_initial_manifest_and_adds_recordings(tmp_path) -> None:
    storage = SessionStore(tmp_path)

    session_id = storage.create_session(
        session_id="ses_demo",
        display_name="demo session",
        metadata={"operator": "alice"},
        created_at_ns=123,
    )
    storage.add_recording_to_session(session_id, "rec_a", updated_at_ns=456)
    storage.add_recording_to_session(session_id, "rec_b", updated_at_ns=789)
    storage.add_recording_to_session(session_id, "rec_b", updated_at_ns=999)

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


def test_experiment_store_creates_initial_manifest_and_adds_sessions(tmp_path) -> None:
    storage = ExperimentStore(tmp_path)

    experiment_id = storage.create_experiment(
        experiment_id="exp_demo",
        display_name="demo experiment",
        metadata={"study": "visual"},
        created_at_ns=321,
    )
    storage.add_session_to_experiment(experiment_id, "ses_a", updated_at_ns=654)
    storage.add_session_to_experiment(experiment_id, "ses_b", updated_at_ns=987)
    storage.add_session_to_experiment(experiment_id, "ses_b", updated_at_ns=1_111)

    assert experiment_id == "exp_demo"
    payload = json.loads(
        (tmp_path / "experiments" / experiment_id / "experiment.json").read_text(
            encoding="utf-8"
        )
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
