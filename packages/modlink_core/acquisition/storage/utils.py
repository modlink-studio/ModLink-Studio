from __future__ import annotations

import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from packages.modlink_shared import FrameEnvelope, StreamDescriptor

SCHEMA_VERSION = 1
WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "COM1",
    "COM2",
    "COM3",
    "COM4",
    "COM5",
    "COM6",
    "COM7",
    "COM8",
    "COM9",
    "LPT1",
    "LPT2",
    "LPT3",
    "LPT4",
    "LPT5",
    "LPT6",
    "LPT7",
    "LPT8",
    "LPT9",
}


def clone_descriptor_snapshot(
    descriptors: dict[str, StreamDescriptor],
) -> dict[str, StreamDescriptor]:
    return {
        stream_id: StreamDescriptor(
            stream_id=descriptor.stream_id,
            modality=descriptor.modality,
            payload_type=descriptor.payload_type,
            nominal_sample_rate_hz=descriptor.nominal_sample_rate_hz,
            chunk_size=descriptor.chunk_size,
            display_name=descriptor.display_name,
            metadata=json.loads(
                json.dumps(to_json_value(descriptor.metadata), ensure_ascii=False)
            ),
        )
        for stream_id, descriptor in descriptors.items()
    }


def descriptor_to_dict(descriptor: StreamDescriptor) -> dict[str, Any]:
    return {
        "stream_id": descriptor.stream_id,
        "modality": descriptor.modality,
        "payload_type": descriptor.payload_type,
        "nominal_sample_rate_hz": descriptor.nominal_sample_rate_hz,
        "chunk_size": descriptor.chunk_size,
        "display_name": descriptor.display_name,
        "metadata": to_json_value(descriptor.metadata),
    }


def format_recording_id(timestamp_ns: int) -> str:
    dt = datetime.fromtimestamp(timestamp_ns / 1_000_000_000, tz=UTC)
    return f"{dt.strftime('%Y%m%dT%H%M%S')}_{timestamp_ns % 1_000_000_000:09d}Z"


def sanitize_path_component(value: str, *, fallback: str) -> str:
    normalized = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", value.strip())
    normalized = re.sub(r"\s+", "_", normalized).strip(" .")
    if not normalized:
        normalized = fallback
    if normalized.upper() in WINDOWS_RESERVED_NAMES:
        normalized = f"_{normalized}"
    return normalized


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


def nominal_sample_period_ns(descriptor: StreamDescriptor) -> int:
    return int(round(1_000_000_000 / nominal_sample_rate_hz(descriptor)))


def derived_timestamp_ns(start_ns: int, sample_index: int, period_ns: int) -> int:
    return int(start_ns) + (sample_index * period_ns)


def derived_timestamps_ns(start_ns: int, sample_count: int, period_ns: int) -> np.ndarray:
    return np.asarray(start_ns, dtype=np.int64) + (
        np.arange(sample_count, dtype=np.int64) * int(period_ns)
    )


def channel_headers(descriptor: StreamDescriptor, channel_count: int) -> list[str]:
    channel_names = descriptor.metadata.get("channel_names")
    if (
        isinstance(channel_names, list)
        and all(isinstance(name, str) and name for name in channel_names)
        and len(channel_names) == channel_count
    ):
        return list(channel_names)
    return [f"channel_{index}" for index in range(channel_count)]
