from __future__ import annotations

from typing import Any

import numpy as np
import pytest

from modlink_sdk import FrameEnvelope, StreamDescriptor


@pytest.fixture
def descriptor_factory():
    def build(
        *,
        payload_type: str = "signal",
        device_id: str = "demo.01",
        stream_key: str = "demo",
        nominal_sample_rate_hz: float = 10.0,
        chunk_size: int = 4,
        channel_names: tuple[str, ...] | None = None,
        display_name: str | None = "Demo Stream",
        metadata: dict[str, Any] | None = None,
    ) -> StreamDescriptor:
        resolved_channel_names = (
            ("ch0", "ch1")
            if channel_names is None and payload_type == "signal"
            else ()
            if channel_names is None
            else channel_names
        )
        return StreamDescriptor(
            device_id=device_id,
            stream_key=stream_key,
            payload_type=payload_type,  # type: ignore[arg-type]
            nominal_sample_rate_hz=nominal_sample_rate_hz,
            chunk_size=chunk_size,
            channel_names=resolved_channel_names,
            display_name=display_name,
            metadata={} if metadata is None else dict(metadata),
        )

    return build


@pytest.fixture
def frame_factory():
    def build(
        descriptor: StreamDescriptor,
        *,
        timestamp_ns: int = 1_000_000_000,
        seq: int | None = 7,
        data: np.ndarray | None = None,
        dtype: np.dtype[Any] | type[np.generic] | type[object] | None = None,
        channel_count: int | None = None,
        chunk_size: int | None = None,
        line_length: int = 5,
        height: int = 3,
        width: int = 4,
    ) -> FrameEnvelope:
        if data is None:
            resolved_chunk_size = descriptor.chunk_size if chunk_size is None else chunk_size
            resolved_channel_count = (
                channel_count
                if channel_count is not None
                else len(descriptor.channel_names)
                if descriptor.channel_names
                else 2
            )
            resolved_dtype = np.dtype(dtype or _default_dtype(descriptor.payload_type))
            data = _build_default_array(
                descriptor.payload_type,
                channel_count=resolved_channel_count,
                chunk_size=resolved_chunk_size,
                line_length=line_length,
                height=height,
                width=width,
                dtype=resolved_dtype,
            )

        return FrameEnvelope(
            device_id=descriptor.device_id,
            stream_key=descriptor.stream_key,
            timestamp_ns=timestamp_ns,
            data=data,
            seq=seq,
        )

    return build


def _default_dtype(payload_type: str) -> np.dtype[Any]:
    if payload_type == "video":
        return np.dtype(np.uint8)
    return np.dtype(np.float32)


def _build_default_array(
    payload_type: str,
    *,
    channel_count: int,
    chunk_size: int,
    line_length: int,
    height: int,
    width: int,
    dtype: np.dtype[Any],
) -> np.ndarray:
    if payload_type == "signal":
        size = channel_count * chunk_size
        return np.arange(size, dtype=dtype).reshape(channel_count, chunk_size)
    if payload_type == "raster":
        size = channel_count * chunk_size * line_length
        return np.arange(size, dtype=dtype).reshape(
            channel_count,
            chunk_size,
            line_length,
        )
    if payload_type in {"field", "video"}:
        size = channel_count * chunk_size * height * width
        return np.arange(size, dtype=dtype).reshape(
            channel_count,
            chunk_size,
            height,
            width,
        )
    raise ValueError(f"unsupported payload_type {payload_type!r}")
