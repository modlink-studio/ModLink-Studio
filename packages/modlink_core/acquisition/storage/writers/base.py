from __future__ import annotations

from pathlib import Path
from typing import Any

from packages.modlink_shared import FrameEnvelope, StreamDescriptor

from ..utils import (
    SCHEMA_VERSION,
    declared_chunk_size,
    descriptor_to_dict,
    nominal_sample_period_ns,
    nominal_sample_rate_hz,
    write_json,
)


class BaseStreamRecordingWriter:
    def __init__(
        self,
        stream_dir: Path,
        descriptor: StreamDescriptor,
    ) -> None:
        self.stream_dir = stream_dir
        self.descriptor = descriptor
        self._frame_count = 0
        self._sample_count = 0
        self._declared_chunk_size = declared_chunk_size(descriptor)
        self._nominal_sample_rate_hz = nominal_sample_rate_hz(descriptor)
        self._sample_period_ns = nominal_sample_period_ns(descriptor)

        self.stream_dir.mkdir(parents=True, exist_ok=True)
        write_json(self.stream_dir / "descriptor.json", descriptor_to_dict(descriptor))

    @property
    def frame_count(self) -> int:
        return self._frame_count

    @property
    def sample_count(self) -> int:
        return self._sample_count

    def append_frame(self, frame: FrameEnvelope) -> None:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError

    def _validate_chunk_size(self, frame: FrameEnvelope, chunk_size: int) -> None:
        if chunk_size != self._declared_chunk_size:
            raise ValueError(
                f"stream_id={frame.stream_id}: chunk_size changed from {self._declared_chunk_size} to {chunk_size}"
            )

    def _write_index(self, **extra_payload: Any) -> None:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "stream_id": self.descriptor.stream_id,
            "modality": self.descriptor.modality,
            "display_name": self.descriptor.display_name,
            "payload_type": self.descriptor.payload_type,
            "frame_count": self.frame_count,
            "sample_count": self.sample_count,
            "nominal_sample_rate_hz": self._nominal_sample_rate_hz,
            "declared_chunk_size": self._declared_chunk_size,
        }
        payload.update(extra_payload)
        write_json(self.stream_dir / "index.json", payload)
