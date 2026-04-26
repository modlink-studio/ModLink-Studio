from __future__ import annotations

import numpy as np

from modlink_core.storage._internal.files import (
    append_csv_row,
    atomic_write_text,
    read_csv_rows,
    read_json,
    to_json_text,
    to_json_value,
    write_csv_header,
    write_json,
    write_npz,
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


def test_csv_helpers_write_and_append_rows(tmp_path) -> None:
    target = tmp_path / "rows.csv"

    write_csv_header(target, ["a", "b"])
    append_csv_row(target, [1, "x"])
    append_csv_row(target, [2, "y"])

    assert read_csv_rows(target) == [
        {"a": "1", "b": "x"},
        {"a": "2", "b": "y"},
    ]
