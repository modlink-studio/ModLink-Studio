from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import pytest

from modlink_core.storage.recordings import StreamRecordingWriter


def test_stream_recording_writer_rejects_unknown_payload_type(
    tmp_path,
    descriptor_factory,
) -> None:
    descriptor = descriptor_factory(payload_type="unknown")  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="unsupported payload_type 'unknown'"):
        StreamRecordingWriter(tmp_path / "unknown", descriptor)


@pytest.mark.parametrize(
    ("payload_type", "frame_kwargs", "expected_shape", "shape_kind", "sample_shape"),
    [
        (
            "signal",
            {"channel_count": 2, "chunk_size": 3, "dtype": np.float32},
            (2, 3),
            "channels_by_time",
            [],
        ),
        (
            "raster",
            {"channel_count": 2, "chunk_size": 3, "line_length": 6, "dtype": np.float32},
            (2, 3, 6),
            "channels_by_time_by_width",
            [6],
        ),
        (
            "field",
            {"channel_count": 2, "chunk_size": 3, "height": 4, "width": 5, "dtype": np.float32},
            (2, 3, 4, 5),
            "channels_by_time_by_height_by_width",
            [4, 5],
        ),
        (
            "video",
            {"channel_count": 3, "chunk_size": 3, "height": 2, "width": 4, "dtype": np.uint8},
            (3, 3, 2, 4),
            "channels_by_time_by_height_by_width",
            [2, 4],
        ),
    ],
)
def test_chunked_writers_persist_uniform_stream_manifests_and_chunks(
    tmp_path,
    descriptor_factory,
    frame_factory,
    payload_type: str,
    frame_kwargs: dict[str, object],
    expected_shape: tuple[int, ...],
    shape_kind: str,
    sample_shape: list[int],
) -> None:
    descriptor = descriptor_factory(
        payload_type=payload_type,
        nominal_sample_rate_hz=20.0,
        chunk_size=3,
        display_name="Demo Stream",
        metadata={"unit": "demo"},
    )
    stream_dir = tmp_path / payload_type
    writer = StreamRecordingWriter(stream_dir, descriptor)

    frame = frame_factory(
        descriptor,
        timestamp_ns=500,
        seq=11,
        extra={"tag": "demo"},
        **frame_kwargs,
    )
    writer.append_frame(frame)
    writer.close()

    stream_payload = _read_json(stream_dir / "stream.json")
    chunk_rows = _read_csv_rows(stream_dir / "chunks.csv")
    with np.load(stream_dir / "chunks" / "chunk-000001.npz") as archive:
        np.testing.assert_array_equal(archive["data"], np.ascontiguousarray(frame.data))
        np.testing.assert_array_equal(
            archive["timestamps_ns"],
            np.asarray([500, 50_000_500, 100_000_500], dtype=np.int64),
        )
        manifest = json.loads(str(archive["manifest_json"].tolist()))

    assert tuple(frame.data.shape) == expected_shape
    assert stream_payload["descriptor"]["display_name"] == "Demo Stream"
    assert stream_payload["storage_kind"] == "npz_chunks"
    assert stream_payload["shape_kind"] == shape_kind
    assert stream_payload["frame_count"] == 1
    assert stream_payload["sample_count"] == 3
    assert stream_payload["chunk_count"] == 1
    assert stream_payload["channel_count"] == expected_shape[0]
    assert stream_payload["sample_shape"] == sample_shape
    assert chunk_rows == [
        {
            "chunk_index": "1",
            "chunk_seq": "11",
            "chunk_start_timestamp_ns": "500",
            "sample_count": "3",
            "file_name": "chunk-000001.npz",
            "shape_json": json.dumps(list(expected_shape)),
            "dtype": frame.data.dtype.str,
            "extra_json": '{"tag": "demo"}',
        }
    ]
    assert manifest["shape"] == list(expected_shape)
    assert manifest["dtype"] == frame.data.dtype.str
    assert manifest["extra"] == {"tag": "demo"}


def test_stream_recording_writer_rejects_signal_chunk_size_drift(
    tmp_path,
    descriptor_factory,
    frame_factory,
) -> None:
    descriptor = descriptor_factory(payload_type="signal", chunk_size=2)
    writer = StreamRecordingWriter(tmp_path / "signal_chunk_drift", descriptor)

    try:
        with pytest.raises(ValueError, match="chunk_size changed from 2 to 3"):
            writer.append_frame(frame_factory(descriptor, chunk_size=3))
    finally:
        writer.close()


def test_stream_recording_writer_rejects_signal_channel_count_drift(
    tmp_path,
    descriptor_factory,
    frame_factory,
) -> None:
    descriptor = descriptor_factory(payload_type="signal", chunk_size=2, channel_names=("a", "b"))
    writer = StreamRecordingWriter(tmp_path / "signal_channels", descriptor)

    try:
        writer.append_frame(frame_factory(descriptor, channel_count=2))
        with pytest.raises(ValueError, match="channel count changed from 2 to 3"):
            writer.append_frame(frame_factory(descriptor, channel_count=3))
    finally:
        writer.close()


@pytest.mark.parametrize(
    ("frame_kwargs", "message"),
    [
        ({"line_length": 7}, r"sample shape changed from \(5,\) to \(7,\)"),
        ({"dtype": np.float64}, "dtype changed from <f4 to <f8"),
        ({"channel_count": 3}, "channel count changed from 2 to 3"),
    ],
)
def test_stream_recording_writer_rejects_raster_shape_and_dtype_drift(
    tmp_path,
    descriptor_factory,
    frame_factory,
    frame_kwargs: dict[str, object],
    message: str,
) -> None:
    descriptor = descriptor_factory(payload_type="raster", chunk_size=2)
    writer = StreamRecordingWriter(tmp_path / "raster_drift", descriptor)
    base_kwargs = {"channel_count": 2, "line_length": 5, "dtype": np.float32}

    try:
        writer.append_frame(frame_factory(descriptor, **base_kwargs))
        with pytest.raises(ValueError, match=message):
            writer.append_frame(frame_factory(descriptor, **(base_kwargs | frame_kwargs)))
    finally:
        writer.close()


@pytest.mark.parametrize(
    ("frame_kwargs", "message"),
    [
        ({"height": 5}, r"sample shape changed from \(3, 4\) to \(5, 4\)"),
        ({"dtype": np.float64}, "dtype changed from <f4 to <f8"),
        ({"channel_count": 3}, "channel count changed from 2 to 3"),
    ],
)
def test_stream_recording_writer_rejects_field_shape_and_dtype_drift(
    tmp_path,
    descriptor_factory,
    frame_factory,
    frame_kwargs: dict[str, object],
    message: str,
) -> None:
    descriptor = descriptor_factory(payload_type="field", chunk_size=2)
    writer = StreamRecordingWriter(tmp_path / "field_drift", descriptor)
    base_kwargs = {"channel_count": 2, "height": 3, "width": 4, "dtype": np.float32}

    try:
        writer.append_frame(frame_factory(descriptor, **base_kwargs))
        with pytest.raises(ValueError, match=message):
            writer.append_frame(frame_factory(descriptor, **(base_kwargs | frame_kwargs)))
    finally:
        writer.close()


@pytest.mark.parametrize(
    ("frame_kwargs", "message"),
    [
        ({"width": 6}, r"sample shape changed from \(3, 4\) to \(3, 6\)"),
        ({"dtype": np.int16}, "dtype changed from |u1 to <i2"),
        ({"channel_count": 4}, "channel count changed from 2 to 4"),
    ],
)
def test_stream_recording_writer_rejects_video_shape_and_dtype_drift(
    tmp_path,
    descriptor_factory,
    frame_factory,
    frame_kwargs: dict[str, object],
    message: str,
) -> None:
    descriptor = descriptor_factory(payload_type="video", chunk_size=2)
    writer = StreamRecordingWriter(tmp_path / "video_drift", descriptor)
    base_kwargs = {"channel_count": 2, "height": 3, "width": 4, "dtype": np.uint8}

    try:
        writer.append_frame(frame_factory(descriptor, **base_kwargs))
        with pytest.raises(ValueError, match=message):
            writer.append_frame(frame_factory(descriptor, **(base_kwargs | frame_kwargs)))
    finally:
        writer.close()


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))
