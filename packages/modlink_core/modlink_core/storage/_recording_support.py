from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import numpy as np

from modlink_sdk import FrameEnvelope, StreamDescriptor

from .io import read_csv_rows, to_json_value


def descriptor_to_dict(descriptor: StreamDescriptor) -> dict[str, Any]:
    return {
        "device_id": descriptor.device_id,
        "stream_id": descriptor.stream_id,
        "stream_key": descriptor.stream_key,
        "payload_type": descriptor.payload_type,
        "nominal_sample_rate_hz": descriptor.nominal_sample_rate_hz,
        "chunk_size": descriptor.chunk_size,
        "channel_names": to_json_value(descriptor.channel_names),
        "display_name": descriptor.display_name,
        "metadata": to_json_value(descriptor.metadata),
    }


def descriptor_from_dict(payload: dict[str, Any]) -> StreamDescriptor:
    return StreamDescriptor(
        device_id=str(payload["device_id"]),
        stream_key=str(payload["stream_key"]),
        payload_type=str(payload["payload_type"]),  # type: ignore[arg-type]
        nominal_sample_rate_hz=float(payload["nominal_sample_rate_hz"]),
        chunk_size=int(payload["chunk_size"]),
        channel_names=tuple(str(item) for item in payload.get("channel_names", [])),
        display_name=None if payload.get("display_name") is None else str(payload["display_name"]),
        metadata={} if not isinstance(payload.get("metadata"), dict) else dict(payload["metadata"]),
    )


def normalize_data_array(frame: FrameEnvelope) -> np.ndarray:
    data = np.asarray(frame.data)
    if data.dtype == np.dtype("O"):
        raise ValueError(f"stream_id={frame.stream_id}: object dtype arrays are not supported")
    return np.ascontiguousarray(data)


def write_csv_header(path: Path, columns: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(columns)


def append_csv_row(path: Path, values: list[object]) -> None:
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(values)


def next_frame_index(path: Path) -> int:
    return len(read_csv_rows(path)) + 1
