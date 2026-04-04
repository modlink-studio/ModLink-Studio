from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import pytest

from modlink_core.acquisition.storage.writers import (
    FieldStreamRecordingWriter,
    RasterStreamRecordingWriter,
    SignalStreamRecordingWriter,
    VideoStreamRecordingWriter,
    create_stream_writer,
)


def test_create_stream_writer_dispatches_supported_payload_types(
    tmp_path,
    descriptor_factory,
) -> None:
    cases = [
        ("signal", SignalStreamRecordingWriter),
        ("raster", RasterStreamRecordingWriter),
        ("field", FieldStreamRecordingWriter),
        ("video", VideoStreamRecordingWriter),
    ]

    for payload_type, expected_cls in cases:
        descriptor = descriptor_factory(payload_type=payload_type)
        writer = create_stream_writer(tmp_path / payload_type, descriptor)
        try:
            assert isinstance(writer, expected_cls)
        finally:
            writer.close()


def test_create_stream_writer_rejects_unknown_payload_type(tmp_path, descriptor_factory) -> None:
    descriptor = descriptor_factory(payload_type="unknown")  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="unsupported payload_type 'unknown'"):
        create_stream_writer(tmp_path / "unknown", descriptor)


def test_signal_writer_persists_csv_and_index(tmp_path, descriptor_factory, frame_factory) -> None:
    descriptor = descriptor_factory(
        payload_type="signal",
        nominal_sample_rate_hz=5.0,
        chunk_size=3,
        channel_names=("f3", "f4"),
        display_name="Signal Demo",
        metadata={"unit": "uV"},
    )
    stream_dir = tmp_path / "signal"
    writer = SignalStreamRecordingWriter(stream_dir, descriptor)

    writer.append_frame(
        frame_factory(
            descriptor,
            timestamp_ns=1_000_000_000,
            seq=9,
            extra={"gain": np.int64(2)},
            channel_count=2,
        )
    )
    writer.close()

    descriptor_payload = _read_json(stream_dir / "descriptor.json")
    index_payload = _read_json(stream_dir / "index.json")
    rows = _read_csv_rows(stream_dir / "data.csv")

    assert descriptor_payload["display_name"] == "Signal Demo"
    assert index_payload == {
        "schema_version": 1,
        "stream_id": descriptor.stream_id,
        "modality": descriptor.modality,
        "display_name": "Signal Demo",
        "payload_type": "signal",
        "frame_count": 1,
        "sample_count": 3,
        "nominal_sample_rate_hz": 5.0,
        "declared_chunk_size": 3,
        "writer_kind": "signal_csv",
        "channel_columns": ["f3", "f4"],
    }
    assert rows == [
        {
            "timestamp_ns": "1000000000",
            "chunk_seq": "9",
            "sample_index_in_chunk": "0",
            "f3": "0.0",
            "f4": "3.0",
            "extra_json": '{"gain": 2}',
        },
        {
            "timestamp_ns": "1200000000",
            "chunk_seq": "9",
            "sample_index_in_chunk": "1",
            "f3": "1.0",
            "f4": "4.0",
            "extra_json": '{"gain": 2}',
        },
        {
            "timestamp_ns": "1400000000",
            "chunk_seq": "9",
            "sample_index_in_chunk": "2",
            "f3": "2.0",
            "f4": "5.0",
            "extra_json": '{"gain": 2}',
        },
    ]


def test_signal_writer_falls_back_to_generated_channel_names(
    tmp_path,
    descriptor_factory,
    frame_factory,
) -> None:
    descriptor = descriptor_factory(
        payload_type="signal",
        chunk_size=2,
        channel_names=("only_one",),
    )
    writer = SignalStreamRecordingWriter(tmp_path / "signal_fallback", descriptor)

    writer.append_frame(frame_factory(descriptor, channel_count=2))
    writer.close()

    rows = _read_csv_rows(tmp_path / "signal_fallback" / "data.csv")

    assert list(rows[0]) == [
        "timestamp_ns",
        "chunk_seq",
        "sample_index_in_chunk",
        "channel_0",
        "channel_1",
        "extra_json",
    ]


def test_signal_writer_rejects_chunk_size_drift(tmp_path, descriptor_factory, frame_factory) -> None:
    descriptor = descriptor_factory(payload_type="signal", chunk_size=2)
    writer = SignalStreamRecordingWriter(tmp_path / "signal_chunk_drift", descriptor)

    try:
        with pytest.raises(ValueError, match="chunk_size changed from 2 to 3"):
            writer.append_frame(frame_factory(descriptor, chunk_size=3))
    finally:
        writer.close()


def test_signal_writer_rejects_channel_count_drift(
    tmp_path,
    descriptor_factory,
    frame_factory,
) -> None:
    descriptor = descriptor_factory(payload_type="signal", chunk_size=2, channel_names=("a", "b"))
    writer = SignalStreamRecordingWriter(tmp_path / "signal_channels", descriptor)

    try:
        writer.append_frame(frame_factory(descriptor, channel_count=2))
        with pytest.raises(ValueError, match="channel count changed from 2 to 3"):
            writer.append_frame(frame_factory(descriptor, channel_count=3))
    finally:
        writer.close()


@pytest.mark.parametrize(
    ("payload_type", "writer_cls", "frame_kwargs", "expected_shape", "index_assertions"),
    [
        (
            "raster",
            RasterStreamRecordingWriter,
            {"channel_count": 2, "chunk_size": 3, "line_length": 6, "dtype": np.float32},
            (2, 3, 6),
            {
                "writer_kind": "raster_npz_chunks",
                "channel_count": 2,
                "line_length": 6,
                "chunk_count": 1,
            },
        ),
        (
            "field",
            FieldStreamRecordingWriter,
            {"channel_count": 2, "chunk_size": 3, "height": 4, "width": 5, "dtype": np.float32},
            (2, 3, 4, 5),
            {
                "writer_kind": "field_npz_chunks",
                "channel_count": 2,
                "spatial_shape": [4, 5],
                "chunk_count": 1,
            },
        ),
        (
            "video",
            VideoStreamRecordingWriter,
            {"channel_count": 3, "chunk_size": 3, "height": 2, "width": 4, "dtype": np.uint8},
            (3, 3, 2, 4),
            {
                "writer_kind": "video_npz_chunks",
                "channel_count": 3,
                "spatial_shape": [2, 4],
                "chunk_count": 1,
                "stored_frame_count": 3,
            },
        ),
    ],
)
def test_npz_writers_persist_chunks_and_indexes(
    tmp_path,
    descriptor_factory,
    frame_factory,
    payload_type: str,
    writer_cls,
    frame_kwargs: dict[str, object],
    expected_shape: tuple[int, ...],
    index_assertions: dict[str, object],
) -> None:
    descriptor = descriptor_factory(
        payload_type=payload_type,
        nominal_sample_rate_hz=20.0,
        chunk_size=3,
    )
    stream_dir = tmp_path / payload_type
    writer = writer_cls(stream_dir, descriptor)

    frame = frame_factory(
        descriptor,
        timestamp_ns=500,
        seq=11,
        extra={"tag": "demo"},
        **frame_kwargs,
    )
    writer.append_frame(frame)
    writer.close()

    index_payload = _read_json(stream_dir / "index.json")
    chunk_rows = _read_csv_rows(stream_dir / "chunks.csv")
    with np.load(stream_dir / "chunks" / "chunk-000001.npz") as archive:
        np.testing.assert_array_equal(archive["data"], np.ascontiguousarray(frame.data))
        np.testing.assert_array_equal(
            archive["timestamps_ns"],
            np.asarray([500, 50_000_500, 100_000_500], dtype=np.int64),
        )
        manifest = json.loads(str(archive["manifest_json"].tolist()))

    assert tuple(frame.data.shape) == expected_shape
    assert index_payload["frame_count"] == 1
    assert index_payload["sample_count"] == 3
    for key, value in index_assertions.items():
        assert index_payload[key] == value
    assert chunk_rows[0]["chunk_seq"] == "11"
    assert chunk_rows[0]["dtype"] == frame.data.dtype.str
    assert manifest["shape"] == list(expected_shape)
    assert manifest["dtype"] == frame.data.dtype.str
    assert manifest["extra"] == {"tag": "demo"}


@pytest.mark.parametrize(
    ("frame_kwargs", "message"),
    [
        ({"line_length": 7}, "line length changed from 5 to 7"),
        ({"dtype": np.float64}, "dtype changed from <f4 to <f8"),
        ({"channel_count": 3}, "channel count changed from 2 to 3"),
    ],
)
def test_raster_writer_rejects_shape_and_dtype_drift(
    tmp_path,
    descriptor_factory,
    frame_factory,
    frame_kwargs: dict[str, object],
    message: str,
) -> None:
    descriptor = descriptor_factory(payload_type="raster", chunk_size=2)
    writer = RasterStreamRecordingWriter(tmp_path / "raster_drift", descriptor)
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
        ({"height": 5}, r"spatial shape changed from \(3, 4\) to \(5, 4\)"),
        ({"dtype": np.float64}, "dtype changed from <f4 to <f8"),
        ({"channel_count": 3}, "channel count changed from 2 to 3"),
    ],
)
def test_field_writer_rejects_shape_and_dtype_drift(
    tmp_path,
    descriptor_factory,
    frame_factory,
    frame_kwargs: dict[str, object],
    message: str,
) -> None:
    descriptor = descriptor_factory(payload_type="field", chunk_size=2)
    writer = FieldStreamRecordingWriter(tmp_path / "field_drift", descriptor)
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
        ({"width": 6}, r"spatial shape changed from \(3, 4\) to \(3, 6\)"),
        ({"dtype": np.int16}, "dtype changed from |u1 to <i2"),
        ({"channel_count": 4}, "channel count changed from 2 to 4"),
    ],
)
def test_video_writer_rejects_shape_and_dtype_drift(
    tmp_path,
    descriptor_factory,
    frame_factory,
    frame_kwargs: dict[str, object],
    message: str,
) -> None:
    descriptor = descriptor_factory(payload_type="video", chunk_size=2)
    writer = VideoStreamRecordingWriter(tmp_path / "video_drift", descriptor)
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
