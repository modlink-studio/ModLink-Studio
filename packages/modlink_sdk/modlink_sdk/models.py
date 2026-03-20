from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, TypeAlias

import numpy as np

PayloadType: TypeAlias = Literal["line", "plane", "video"]


@dataclass(slots=True)
class FrameEnvelope:
    stream_id: str
    timestamp_ns: int
    data: np.ndarray
    seq: int | None = None
    extra: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class StreamDescriptor:
    stream_id: str
    modality: str
    payload_type: PayloadType
    nominal_sample_rate_hz: float
    chunk_size: int
    display_name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
