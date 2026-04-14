from __future__ import annotations

import json

import numpy as np
import pytest

from modlink_core.storage.io import (
    atomic_write_text,
    to_json_text,
    to_json_value,
    read_json,
    write_json,
    write_npz,
)
from modlink_core.storage.recordings import (
    declared_chunk_size,
    descriptor_to_dict,
    nominal_sample_rate_hz,
    normalize_data_array,
)


def test_to_json_value_normalizes_numpy_and_nested_values() -> None:
    class Stringable:
        def __str__(self) -> str:
            return "stringable"

    payload = {
        1: np.int64(2),
        "array": np.asarray([[1, 2], [3, 4]], dtype=np.int16),
        "tuple": (np.float32(1.5), True),
        "dict": {np.int64(9): Stringable()},
    }

    result = to_json_value(payload)

    assert result == {
        "1": 2,
        "array": [[1, 2], [3, 4]],
        "tuple": [1.5, True],
        "dict": {"9": "stringable"},
    }


def test_to_json_text_emits_stable_sorted_json() -> None:
    payload = {
        "b": np.asarray([2, 3], dtype=np.int16),
        "a": {"y": np.int64(4), "x": np.float32(1.25)},
    }

    assert to_json_text(payload) == '{"a": {"x": 1.25, "y": 4}, "b": [2, 3]}'


def test_normalize_data_array_returns_contiguous_copy(frame_factory, descriptor_factory) -> None:
    descriptor = descriptor_factory(payload_type="signal", chunk_size=3)
    data = np.asfortranarray(np.arange(6, dtype=np.float32).reshape(2, 3))
    frame = frame_factory(descriptor, data=data)

    normalized = normalize_data_array(frame, expected_ndim=2)

    np.testing.assert_array_equal(normalized, data)
    assert normalized.flags.c_contiguous


def test_normalize_data_array_rejects_object_dtype(frame_factory, descriptor_factory) -> None:
    descriptor = descriptor_factory(payload_type="signal", chunk_size=2)
    frame = frame_factory(
        descriptor,
        data=np.asarray([["bad", object()]], dtype=object),
    )

    with pytest.raises(ValueError, match="object dtype arrays are not supported"):
        normalize_data_array(frame, expected_ndim=2)


def test_normalize_data_array_rejects_wrong_dimension(frame_factory, descriptor_factory) -> None:
    descriptor = descriptor_factory(payload_type="signal", chunk_size=2)
    frame = frame_factory(descriptor, data=np.arange(4, dtype=np.float32))

    with pytest.raises(ValueError, match="expected data.ndim == 2, got 1"):
        normalize_data_array(frame, expected_ndim=2)


@pytest.mark.parametrize("value", ["abc", None, 0, -3])
def test_declared_chunk_size_rejects_invalid_values(descriptor_factory, value: object) -> None:
    descriptor = descriptor_factory(chunk_size=value)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="descriptor.chunk_size must"):
        declared_chunk_size(descriptor)


@pytest.mark.parametrize("value", ["abc", None, 0, -1.0])
def test_nominal_sample_rate_rejects_invalid_values(descriptor_factory, value: object) -> None:
    descriptor = descriptor_factory(nominal_sample_rate_hz=value)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="descriptor.nominal_sample_rate_hz must"):
        nominal_sample_rate_hz(descriptor)


def test_descriptor_to_dict_serializes_public_fields(descriptor_factory) -> None:
    descriptor = descriptor_factory(
        payload_type="field",
        channel_names=("c3", "c4"),
        display_name="Field Demo",
        metadata={"scale": np.float32(2.5), "axes": np.asarray([1, 2])},
    )

    payload = descriptor_to_dict(descriptor)

    assert payload == {
        "device_id": descriptor.device_id,
        "stream_id": descriptor.stream_id,
        "modality": descriptor.modality,
        "payload_type": "field",
        "nominal_sample_rate_hz": 10.0,
        "chunk_size": 4,
        "channel_names": ["c3", "c4"],
        "display_name": "Field Demo",
        "metadata": {"axes": [1, 2], "scale": 2.5},
    }


def test_atomic_write_text_replaces_target_without_temp_residue(tmp_path) -> None:
    target = tmp_path / "nested" / "payload.txt"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("old", encoding="utf-8")

    atomic_write_text(target, "new")

    assert target.read_text(encoding="utf-8") == "new"
    assert not list(tmp_path.rglob("*.tmp"))


def test_write_json_persists_sorted_payload_without_temp_residue(tmp_path) -> None:
    target = tmp_path / "payload.json"

    write_json(target, {"b": 2, "a": {"value": 1}})

    assert read_json(target) == {"a": {"value": 1}, "b": 2}
    assert target.read_text(encoding="utf-8").endswith("\n")
    assert not list(tmp_path.rglob("*.tmp"))


def test_write_npz_persists_archive_without_temp_residue(tmp_path) -> None:
    target = tmp_path / "payload.npz"

    write_npz(
        target,
        data=np.arange(6, dtype=np.float32).reshape(2, 3),
        value=np.asarray(7, dtype=np.int64),
    )

    with np.load(target) as archive:
        np.testing.assert_array_equal(
            archive["data"],
            np.arange(6, dtype=np.float32).reshape(2, 3),
        )
        assert archive["value"].item() == 7
    assert not list(tmp_path.rglob("*.tmp"))
