from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import pytest

from modlink_core.storage import append_recording_frame, create_recording
from modlink_core.storage._internal.ids import safe_path_component


@pytest.mark.parametrize(
    ("payload_type", "frame_kwargs", "expected_shape"),
    [
        ("signal", {"channel_count": 2, "chunk_size": 3, "dtype": np.float32}, (2, 3)),
        (
            "raster",
            {"channel_count": 2, "chunk_size": 3, "line_length": 6, "dtype": np.float32},
            (2, 3, 6),
        ),
        (
            "field",
            {"channel_count": 2, "chunk_size": 3, "height": 4, "width": 5, "dtype": np.float32},
            (2, 3, 4, 5),
        ),
        (
            "video",
            {"channel_count": 3, "chunk_size": 3, "height": 2, "width": 4, "dtype": np.uint8},
            (3, 3, 2, 4),
        ),
    ],
)
def test_recording_store_persists_minimal_stream_files(
    tmp_path,
    descriptor_factory,
    frame_factory,
    payload_type: str,
    frame_kwargs: dict[str, object],
    expected_shape: tuple[int, ...],
) -> None:
    descriptor = descriptor_factory(
        payload_type=payload_type,
        nominal_sample_rate_hz=20.0,
        chunk_size=3,
        display_name="Demo Stream",
        metadata={"unit": "demo"},
    )
    recording_id = create_recording(tmp_path, {descriptor.stream_id: descriptor})
    stream_dir = (
        tmp_path
        / "recordings"
        / recording_id
        / "streams"
        / safe_path_component(descriptor.stream_id)
    )

    frame = frame_factory(
        descriptor,
        timestamp_ns=500,
        seq=11,
        **frame_kwargs,
    )
    append_recording_frame(tmp_path, recording_id, frame)

    stream_payload = _read_json(stream_dir / "stream.json")
    frame_rows = _read_csv_rows(stream_dir / "frames.csv")
    with np.load(stream_dir / "frames" / "000001.npz") as archive:
        np.testing.assert_array_equal(archive["data"], np.ascontiguousarray(frame.data))
        assert set(archive.files) == {"data"}

    assert tuple(frame.data.shape) == expected_shape
    assert stream_payload["stream_id"] == descriptor.stream_id
    assert stream_payload["descriptor"]["display_name"] == "Demo Stream"
    assert frame_rows == [
        {
            "frame_index": "1",
            "timestamp_ns": "500",
            "seq": "11",
            "file_name": "000001.npz",
        }
    ]


def test_recording_store_increments_frame_index_for_multiple_appends(
    tmp_path,
    descriptor_factory,
    frame_factory,
) -> None:
    descriptor = descriptor_factory(payload_type="signal", chunk_size=2)
    recording_id = create_recording(tmp_path, {descriptor.stream_id: descriptor})
    frames_index_path = (
        tmp_path
        / "recordings"
        / recording_id
        / "streams"
        / safe_path_component(descriptor.stream_id)
        / "frames.csv"
    )

    append_recording_frame(tmp_path, recording_id, frame_factory(descriptor, timestamp_ns=100, seq=1))
    append_recording_frame(tmp_path, recording_id, frame_factory(descriptor, timestamp_ns=200, seq=2))

    assert _read_csv_rows(frames_index_path) == [
        {
            "frame_index": "1",
            "timestamp_ns": "100",
            "seq": "1",
            "file_name": "000001.npz",
        },
        {
            "frame_index": "2",
            "timestamp_ns": "200",
            "seq": "2",
            "file_name": "000002.npz",
        },
    ]


def test_recording_store_persists_arbitrary_array_shape(
    tmp_path,
    descriptor_factory,
    frame_factory,
) -> None:
    descriptor = descriptor_factory(payload_type="signal", chunk_size=2)
    recording_id = create_recording(tmp_path, {descriptor.stream_id: descriptor})
    stream_dir = (
        tmp_path
        / "recordings"
        / recording_id
        / "streams"
        / safe_path_component(descriptor.stream_id)
    )
    frame = frame_factory(
        descriptor,
        data=np.arange(4, dtype=np.float32),
    )

    append_recording_frame(tmp_path, recording_id, frame)

    with np.load(stream_dir / "frames" / "000001.npz") as archive:
        np.testing.assert_array_equal(archive["data"], frame.data)


def test_recording_store_rejects_object_dtype_arrays(
    tmp_path,
    descriptor_factory,
    frame_factory,
) -> None:
    descriptor = descriptor_factory(payload_type="signal", chunk_size=2)
    recording_id = create_recording(tmp_path, {descriptor.stream_id: descriptor})
    frame = frame_factory(
        descriptor,
        data=np.asarray([["bad", object()]], dtype=object),
    )

    with pytest.raises(ValueError, match="object dtype arrays are not supported"):
        append_recording_frame(tmp_path, recording_id, frame)


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))
