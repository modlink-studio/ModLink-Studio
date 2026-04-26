from __future__ import annotations

import queue
import time
import zipfile
from pathlib import Path

import numpy as np
import pytest

from modlink_core.bus import StreamBus
from modlink_core.event_stream import BackendEventBroker
from modlink_core.models import ExportJobSnapshot, ReplayMarker, ReplaySegment
from modlink_core.replay import ReplayBackend
from modlink_core.replay.reader import RecordingReader
from modlink_core.settings import SettingsStore, declare_core_settings
from modlink_core.storage import (
    add_recording_marker,
    add_recording_segment,
    append_recording_frame,
    create_recording,
    list_recordings,
    load_recording_frame_data,
    read_recording,
    read_recording_frames,
    read_recording_markers,
    read_recording_segments,
    read_recording_stream,
)


def test_recording_storage_read_api_lists_and_reads_valid_recordings(
    tmp_path,
    descriptor_factory,
    frame_factory,
) -> None:
    descriptor = descriptor_factory(payload_type="signal", chunk_size=3, channel_names=("f3", "f4"))
    frame = frame_factory(descriptor, timestamp_ns=1_700_000_000_123_456_789, seq=11)
    recording_id = create_recording(
        tmp_path,
        {descriptor.stream_id: descriptor},
        recording_label="baseline",
    )
    append_recording_frame(tmp_path, recording_id, frame)
    add_recording_marker(tmp_path, recording_id, 1_700_000_000_123_456_999, "start")
    add_recording_segment(
        tmp_path,
        recording_id,
        1_700_000_000_123_456_999,
        1_700_000_000_223_456_999,
        "segment_a",
    )
    (tmp_path / "recordings" / "broken").mkdir(parents=True)

    manifests = list_recordings(tmp_path)

    assert manifests == [
        {
            "recording_id": recording_id,
            "recording_label": "baseline",
            "stream_ids": [descriptor.stream_id],
        }
    ]
    assert read_recording(tmp_path, recording_id) == manifests[0]
    assert (
        read_recording_stream(tmp_path, recording_id, descriptor.stream_id)["stream_id"]
        == descriptor.stream_id
    )
    assert read_recording_markers(tmp_path, recording_id) == [
        {"timestamp_ns": "1700000000123456999", "label": "start"}
    ]
    assert read_recording_segments(tmp_path, recording_id) == [
        {
            "start_ns": "1700000000123456999",
            "end_ns": "1700000000223456999",
            "label": "segment_a",
        }
    ]
    assert read_recording_frames(tmp_path, recording_id, descriptor.stream_id) == [
        {
            "frame_index": "1",
            "timestamp_ns": "1700000000123456789",
            "seq": "11",
            "file_name": "000001.npz",
        }
    ]
    np.testing.assert_array_equal(
        load_recording_frame_data(tmp_path, recording_id, descriptor.stream_id, "000001.npz"),
        np.ascontiguousarray(frame.data),
    )


def test_recording_reader_merges_frames_and_normalizes_annotations(
    tmp_path,
    descriptor_factory,
    frame_factory,
) -> None:
    signal_descriptor = descriptor_factory(
        payload_type="signal",
        stream_key="signal",
        chunk_size=2,
        channel_names=("c3", "c4"),
    )
    raster_descriptor = descriptor_factory(
        payload_type="raster",
        stream_key="raster",
        chunk_size=1,
    )
    recording_id = create_recording(
        tmp_path,
        {
            signal_descriptor.stream_id: signal_descriptor,
            raster_descriptor.stream_id: raster_descriptor,
        },
        recording_label="reader_case",
    )
    append_recording_frame(
        tmp_path,
        recording_id,
        frame_factory(signal_descriptor, timestamp_ns=1_000_000_000, seq=1),
    )
    append_recording_frame(
        tmp_path,
        recording_id,
        frame_factory(raster_descriptor, timestamp_ns=1_050_000_000, seq=2, line_length=4),
    )
    append_recording_frame(
        tmp_path,
        recording_id,
        frame_factory(signal_descriptor, timestamp_ns=1_100_000_000, seq=3),
    )
    add_recording_marker(tmp_path, recording_id, 1_025_000_000, "marker_a")
    add_recording_segment(tmp_path, recording_id, 1_020_000_000, 1_080_000_000, "segment_a")

    reader = RecordingReader(tmp_path / "recordings" / recording_id)

    assert reader.recording_id == recording_id
    assert reader.recording_label == "reader_case"
    assert reader.duration_ns == 100_000_000
    assert reader.stream_ids() == (signal_descriptor.stream_id, raster_descriptor.stream_id)
    assert [ref.stream_id for ref in reader.frames()] == [
        signal_descriptor.stream_id,
        raster_descriptor.stream_id,
        signal_descriptor.stream_id,
    ]
    assert [ref.relative_timestamp_ns for ref in reader.frames()] == [0, 50_000_000, 100_000_000]
    assert reader.markers() == (ReplayMarker(timestamp_ns=25_000_000, label="marker_a"),)
    assert reader.segments() == (
        ReplaySegment(start_ns=20_000_000, end_ns=80_000_000, label="segment_a"),
    )
    envelope = reader.load_frame(reader.frames()[0])
    assert envelope.stream_id == signal_descriptor.stream_id
    assert envelope.seq == 1


def test_replay_backend_replays_on_its_own_bus(
    tmp_path,
    descriptor_factory,
    frame_factory,
) -> None:
    descriptor = descriptor_factory(payload_type="signal", stream_key="signal", chunk_size=2)
    recording_id = create_recording(tmp_path, {descriptor.stream_id: descriptor})
    append_recording_frame(
        tmp_path, recording_id, frame_factory(descriptor, timestamp_ns=1_000_000_000, seq=1)
    )
    append_recording_frame(
        tmp_path, recording_id, frame_factory(descriptor, timestamp_ns=1_050_000_000, seq=2)
    )
    append_recording_frame(
        tmp_path, recording_id, frame_factory(descriptor, timestamp_ns=1_100_000_000, seq=3)
    )

    settings = _build_settings(tmp_path)
    backend = ReplayBackend(settings=settings)
    backend.start()

    try:
        backend.refresh_recordings().result(1.0)
        backend.open_recording(tmp_path / "recordings" / recording_id).result(1.0)
        replay_stream = backend.bus.open_frame_stream(maxsize=8, consumer_name="replay-test")
        live_bus = StreamBus(event_broker=BackendEventBroker())
        live_bus.add_descriptor(descriptor)
        live_stream = live_bus.open_frame_stream(maxsize=8, consumer_name="live-test")

        backend.play().result(1.0)
        received = _read_frames(replay_stream, expected_count=3, timeout=1.5)
        _wait_until(lambda: backend.snapshot().state == "finished", timeout=1.5)

        assert [frame.seq for frame in received] == [1, 2, 3]
        with pytest.raises(queue.Empty):
            live_stream.read(timeout=0.05)

        backend.stop().result(1.0)
        assert backend.snapshot().state == "ready"
        assert backend.snapshot().position_ns == 0
    finally:
        backend.shutdown()


@pytest.mark.parametrize(
    ("format_id", "expected_files"),
    [
        ("signal_csv", ("signal.csv",)),
        ("signal_npz", ("signal.npz", "signal.json")),
        ("raster_npz", ("raster.npz", "raster.json")),
        ("field_npz", ("field.npz", "field.json")),
        ("video_frames_zip", ("video.zip",)),
        ("recording_bundle_zip", ("rec_demo.zip",)),
    ],
)
def test_replay_export_formats_write_expected_outputs(
    tmp_path,
    descriptor_factory,
    frame_factory,
    format_id: str,
    expected_files: tuple[str, ...],
) -> None:
    descriptors = {
        "signal": descriptor_factory(
            payload_type="signal", stream_key="signal", chunk_size=2, channel_names=("c3", "c4")
        ),
        "raster": descriptor_factory(payload_type="raster", stream_key="raster", chunk_size=1),
        "field": descriptor_factory(payload_type="field", stream_key="field", chunk_size=1),
        "video": descriptor_factory(payload_type="video", stream_key="video", chunk_size=1),
    }
    recording_id = create_recording(
        tmp_path,
        {descriptor.stream_id: descriptor for descriptor in descriptors.values()},
        recording_id="rec_demo",
    )
    append_recording_frame(
        tmp_path,
        recording_id,
        frame_factory(descriptors["signal"], timestamp_ns=1_000_000_000, seq=1),
    )
    append_recording_frame(
        tmp_path,
        recording_id,
        frame_factory(descriptors["raster"], timestamp_ns=1_000_000_100, seq=2, line_length=4),
    )
    append_recording_frame(
        tmp_path,
        recording_id,
        frame_factory(descriptors["field"], timestamp_ns=1_000_000_200, seq=3, height=3, width=4),
    )
    append_recording_frame(
        tmp_path,
        recording_id,
        frame_factory(
            descriptors["video"],
            timestamp_ns=1_000_000_300,
            seq=4,
            height=2,
            width=3,
            dtype=np.uint8,
        ),
    )

    settings = _build_settings(tmp_path)
    backend = ReplayBackend(settings=settings)
    backend.start()

    try:
        backend.open_recording(tmp_path / "recordings" / recording_id).result(1.0)
        job = backend.start_export(format_id).result(1.0)
        completed = _wait_for_job(backend, job.job_id, timeout=2.0)
        assert completed.state == "completed"
        assert completed.output_path is not None
        output_dir = Path(completed.output_path)
        assert output_dir.is_dir()
        for file_name in expected_files:
            assert (output_dir / file_name).exists()
        if format_id == "recording_bundle_zip":
            with zipfile.ZipFile(output_dir / "rec_demo.zip") as archive:
                assert "recordings/rec_demo/recording.json" in archive.namelist()
    finally:
        backend.shutdown()


def test_replay_export_job_fails_when_format_has_no_matching_streams(
    tmp_path,
    descriptor_factory,
    frame_factory,
) -> None:
    descriptor = descriptor_factory(payload_type="signal", stream_key="signal", chunk_size=2)
    recording_id = create_recording(tmp_path, {descriptor.stream_id: descriptor})
    append_recording_frame(
        tmp_path, recording_id, frame_factory(descriptor, timestamp_ns=1_000_000_000, seq=1)
    )

    settings = _build_settings(tmp_path)
    backend = ReplayBackend(settings=settings)
    backend.start()

    try:
        backend.open_recording(tmp_path / "recordings" / recording_id).result(1.0)
        job = backend.start_export("field_npz").result(1.0)
        failed = _wait_for_job(backend, job.job_id, timeout=2.0)
        assert failed.state == "failed"
        assert failed.error is not None
    finally:
        backend.shutdown()


def _build_settings(tmp_path: Path) -> SettingsStore:
    settings = SettingsStore()
    declare_core_settings(settings)
    settings.storage.root_dir = str(tmp_path)
    settings.storage.export_root_dir = str(tmp_path / "exports")
    return settings


def _read_frames(frame_stream, *, expected_count: int, timeout: float) -> list:
    deadline = time.time() + timeout
    frames: list = []
    while time.time() < deadline and len(frames) < expected_count:
        try:
            frames.append(frame_stream.read(timeout=0.1))
        except queue.Empty:
            continue
    if len(frames) != expected_count:
        raise AssertionError(f"expected {expected_count} frames, got {len(frames)}")
    return frames


def _wait_until(predicate, *, timeout: float) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return
        time.sleep(0.01)
    if predicate():
        return
    raise AssertionError("condition not reached before timeout")


def _wait_for_job(backend: ReplayBackend, job_id: str, *, timeout: float) -> ExportJobSnapshot:
    deadline = time.time() + timeout
    while time.time() < deadline:
        for job in backend.export_jobs():
            if job.job_id == job_id and job.state in {"completed", "failed"}:
                return job
        time.sleep(0.01)
    raise AssertionError("export job did not finish before timeout")
