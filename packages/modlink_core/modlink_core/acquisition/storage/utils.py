from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import numpy as np

from modlink_sdk import FrameEnvelope, StreamDescriptor

SCHEMA_VERSION = 1


def descriptor_to_dict(descriptor: StreamDescriptor) -> dict[str, Any]:
    return {
        "device_id": descriptor.device_id,
        "stream_id": descriptor.stream_id,
        "modality": descriptor.modality,
        "payload_type": descriptor.payload_type,
        "nominal_sample_rate_hz": descriptor.nominal_sample_rate_hz,
        "chunk_size": descriptor.chunk_size,
        "channel_names": to_json_value(descriptor.channel_names),
        "unit": descriptor.unit,
        "display_name": descriptor.display_name,
        "metadata": to_json_value(descriptor.metadata),
    }


def to_json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, dict):
        return {str(key): to_json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_json_value(item) for item in value]
    return str(value)


def to_json_text(value: Any) -> str:
    return json.dumps(
        to_json_value(value),
        ensure_ascii=False,
        sort_keys=True,
    )


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f"{path.name}.tmp")
    temp_path.write_text(content, encoding="utf-8")
    os.replace(temp_path, path)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    atomic_write_text(
        path,
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )


def write_npz(path: Path, **payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f"{path.name}.tmp")
    with temp_path.open("wb") as handle:
        np.savez_compressed(handle, **payload)
    os.replace(temp_path, path)


def normalize_data_array(frame: FrameEnvelope, *, expected_ndim: int) -> np.ndarray:
    data = np.asarray(frame.data)
    if data.dtype == np.dtype("O"):
        raise ValueError(
            f"stream_id={frame.stream_id}: object dtype arrays are not supported"
        )
    if data.ndim != expected_ndim:
        raise ValueError(
            f"stream_id={frame.stream_id}: expected data.ndim == {expected_ndim}, got {data.ndim}"
        )
    return np.ascontiguousarray(data)


def declared_chunk_size(descriptor: StreamDescriptor) -> int:
    try:
        value = int(descriptor.chunk_size)
    except (TypeError, ValueError):
        raise ValueError(
            f"stream_id={descriptor.stream_id}: descriptor.chunk_size must be a positive integer"
        ) from None
    if value <= 0:
        raise ValueError(
            f"stream_id={descriptor.stream_id}: descriptor.chunk_size must be positive"
        )
    return value


def nominal_sample_rate_hz(descriptor: StreamDescriptor) -> float:
    try:
        value = float(descriptor.nominal_sample_rate_hz)
    except (TypeError, ValueError):
        raise ValueError(
            f"stream_id={descriptor.stream_id}: descriptor.nominal_sample_rate_hz must be positive"
        ) from None
    if value <= 0:
        raise ValueError(
            f"stream_id={descriptor.stream_id}: descriptor.nominal_sample_rate_hz must be positive"
        )
    return value
