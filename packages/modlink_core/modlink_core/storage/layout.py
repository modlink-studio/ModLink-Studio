from __future__ import annotations

import re
from datetime import UTC, datetime

SCHEMA_VERSION = 1


def safe_path_component(value: str) -> str:
    normalized = re.sub(r'[<>:"/\\\\|?*]+', "_", str(value).strip())
    normalized = normalized.rstrip(". ")
    return normalized or "_"


def generate_storage_id(prefix: str, timestamp_ns: int) -> str:
    timestamp = datetime.fromtimestamp(timestamp_ns / 1_000_000_000, tz=UTC)
    return f"{prefix}_{timestamp.strftime('%Y%m%dT%H%M%S')}_{timestamp_ns % 1_000_000_000:09d}Z"


def validate_storage_id(value: str, prefix: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{prefix}_id must not be empty")
    if safe_path_component(normalized) != normalized:
        raise ValueError(f"{prefix}_id contains unsupported path characters")
    return normalized
