from __future__ import annotations

import re

_DEVICE_ID_PATTERN = re.compile(r"^[a-z0-9_]+\.[0-9]{2,}$")
_DEVICE_NAME_PATTERN = re.compile(r"[^a-z0-9_]+")
_MODALITY_PATTERN = re.compile(r"[^a-z0-9_]+")


def normalize_device_name(name: str) -> str:
    """Normalize a driver/device base name to an SDK-safe token."""

    normalized = _DEVICE_NAME_PATTERN.sub("_", str(name).strip().lower())
    normalized = re.sub(r"_+", "_", normalized).strip("._")
    if not normalized:
        raise ValueError("device name must not be empty")
    return normalized


def normalize_modality(modality: str) -> str:
    """Normalize a modality label to an SDK-safe token."""

    normalized = _MODALITY_PATTERN.sub("_", str(modality).strip().lower())
    normalized = re.sub(r"_+", "_", normalized).strip("._")
    if not normalized:
        raise ValueError("modality must not be empty")
    return normalized


def normalize_device_id(device_id: str) -> str:
    """Validate and normalize a canonical ``device_id``."""

    normalized = str(device_id).strip().lower().replace("-", "_")
    normalized = re.sub(r"[^a-z0-9_.]+", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized).strip("._")
    if not _DEVICE_ID_PATTERN.fullmatch(normalized):
        raise ValueError(
            "device_id must match 'name.XX', for example 'my_driver.01'"
        )
    return normalized


def make_device_id(name: str, index: int = 1) -> str:
    """Create a canonical ``device_id`` from a base name and ordinal."""

    ordinal = int(index)
    if ordinal <= 0:
        raise ValueError("device_id index must be positive")
    return f"{normalize_device_name(name)}.{ordinal:02d}"


def make_stream_id(device_id: str, modality: str) -> str:
    """Create the derived ``stream_id`` for one device modality."""

    return f"{normalize_device_id(device_id)}:{normalize_modality(modality)}"
