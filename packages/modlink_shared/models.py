from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class FrameEnvelope:
    stream_id: str
    timestamp_ns: int
    payload: object
    seq: int | None = None


@dataclass(slots=True)
class StreamDescriptor:
    stream_id: str
    modality: str
    payload_type: str
    display_name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
