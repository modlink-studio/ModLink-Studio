"""Shared data models for the scaffold wizard and generator."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

DriverKind = Literal["driver", "loop"]
PayloadType = Literal["signal", "raster", "field", "video"]
DataArrivalPattern = Literal["push", "poll", "unsure"]

DEVICE_ID_PATTERN = re.compile(r"^[a-z0-9_]+\.[0-9]{2,}$")
TOKEN_PATTERN = re.compile(r"[^a-z0-9_]+")


def sanitize_identifier(name: str) -> str:
    """Convert free-form input into a Python/package safe identifier."""
    value = re.sub(r"[^\w\s-]", "", str(name))
    value = re.sub(r"[-\s]+", "_", value)
    value = value.lower().strip("_")
    if value and value[0].isdigit():
        value = f"plugin_{value}"
    return value


def normalize_token(value: str) -> str:
    """Normalize a token used by device ids, modalities, or providers."""
    normalized = TOKEN_PATTERN.sub("_", str(value).strip().lower())
    normalized = re.sub(r"_+", "_", normalized).strip("._")
    return normalized


def to_pascal_case(name: str) -> str:
    parts = re.split(r"[_-]+", str(name))
    return "".join(word.capitalize() for word in parts if word)


def to_title_words(name: str) -> str:
    words = normalize_token(name).split("_")
    return " ".join(word.capitalize() for word in words if word)


def make_device_id(name: str, index: int = 1) -> str:
    base = normalize_token(name)
    if not base:
        raise ValueError("device base name must not be empty")
    ordinal = max(1, int(index))
    return f"{base}.{ordinal:02d}"


def normalize_device_id(device_id: str) -> str:
    normalized = str(device_id).strip().lower().replace("-", "_")
    normalized = re.sub(r"[^a-z0-9_.]+", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized).strip("._")
    return normalized


def is_valid_device_id(device_id: str) -> bool:
    normalized = normalize_device_id(device_id)
    return bool(DEVICE_ID_PATTERN.fullmatch(normalized))


def unique_strings(values: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for raw in values:
        value = str(raw).strip()
        if not value or value in seen:
            continue
        result.append(value)
        seen.add(value)
    return tuple(result)


@dataclass(slots=True)
class StreamSpec:
    modality: str
    payload_type: PayloadType
    display_name: str
    sample_rate_hz: float
    chunk_size: int
    channel_names: tuple[str, ...] = ()
    unit: str | None = None
    raster_length: int | None = None
    field_height: int | None = None
    field_width: int | None = None
    video_height: int | None = None
    video_width: int | None = None

    def __post_init__(self) -> None:
        self.modality = normalize_token(self.modality)
        if not self.modality:
            raise ValueError("stream modality must not be empty")
        self.display_name = str(self.display_name).strip() or f"{to_title_words(self.modality)} Stream"
        self.sample_rate_hz = float(self.sample_rate_hz)
        if self.sample_rate_hz <= 0.0:
            raise ValueError("sample_rate_hz must be positive")
        self.chunk_size = int(self.chunk_size)
        if self.chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        self.channel_names = unique_strings(self.channel_names)

        if self.payload_type == "signal" and not self.channel_names:
            self.channel_names = ("ch1",)
        if self.payload_type == "raster" and not self.channel_names:
            self.channel_names = ("intensity",)
        if self.payload_type == "field" and not self.channel_names:
            self.channel_names = ("intensity",)
        if self.payload_type == "video" and not self.channel_names:
            self.channel_names = ("red", "green", "blue")

        if self.payload_type == "raster":
            self.raster_length = max(1, int(self.raster_length or 1))
        if self.payload_type == "field":
            self.field_height = max(1, int(self.field_height or 1))
            self.field_width = max(1, int(self.field_width or 1))
        if self.payload_type == "video":
            self.video_height = max(1, int(self.video_height or 1))
            self.video_width = max(1, int(self.video_width or 1))

    @property
    def channel_count(self) -> int:
        return len(self.channel_names)

    @property
    def metadata(self) -> dict[str, object]:
        payload: dict[str, object] = {}
        if self.unit:
            payload["unit"] = self.unit
        if self.payload_type == "raster" and self.raster_length is not None:
            payload["length"] = self.raster_length
        if self.payload_type == "field":
            payload["height"] = self.field_height
            payload["width"] = self.field_width
        if self.payload_type == "video":
            payload["height"] = self.video_height
            payload["width"] = self.video_width
        return payload

    @property
    def expected_shape(self) -> str:
        if self.payload_type == "signal":
            return f"[{self.channel_count}, {self.chunk_size}]"
        if self.payload_type == "raster":
            return f"[{self.channel_count}, {self.chunk_size}, {self.raster_length}]"
        if self.payload_type == "field":
            return f"[{self.channel_count}, {self.chunk_size}, {self.field_height}, {self.field_width}]"
        return f"[{self.channel_count}, {self.chunk_size}, {self.video_height}, {self.video_width}]"

    @property
    def loop_interval_ms_suggestion(self) -> int:
        return max(1, int(round(1000.0 * self.chunk_size / self.sample_rate_hz)))


@dataclass(slots=True)
class DriverSpec:
    plugin_name: str
    display_name: str
    device_id: str
    providers: tuple[str, ...]
    driver_kind: DriverKind
    driver_reason: str
    data_arrival: DataArrivalPattern
    streams: tuple[StreamSpec, ...]
    dependencies: tuple[str, ...] = ()
    project_name: str = field(init=False)
    class_name: str = field(init=False)
    entry_point_name: str = field(init=False)

    def __post_init__(self) -> None:
        plugin_identifier = sanitize_identifier(self.plugin_name)
        if not plugin_identifier:
            raise ValueError("plugin_name must contain at least one letter or number")
        self.plugin_name = plugin_identifier
        self.project_name = self.plugin_name.replace("_", "-")
        self.class_name = to_pascal_case(self.plugin_name)
        self.entry_point_name = self.plugin_name.replace("_", "")

        self.display_name = str(self.display_name).strip() or self.class_name
        self.device_id = normalize_device_id(self.device_id)
        if not is_valid_device_id(self.device_id):
            raise ValueError("device_id must match name.XX")
        normalized_providers = tuple(
            provider
            for provider in (normalize_token(item) for item in self.providers)
            if provider
        )
        self.providers = unique_strings(normalized_providers)
        if not self.providers:
            raise ValueError("at least one provider is required")
        self.driver_reason = str(self.driver_reason).strip()
        self.streams = tuple(self.streams)
        if not self.streams:
            raise ValueError("at least one stream is required")

        dependencies = list(self.dependencies)
        dependencies.extend(["modlink-sdk", "numpy>=2.3.3"])
        self.dependencies = unique_strings(dependencies)

    @property
    def driver_base_class(self) -> str:
        return "LoopDriver" if self.driver_kind == "loop" else "Driver"

    @property
    def providers_tuple(self) -> str:
        return repr(self.providers)

    @property
    def providers_display(self) -> str:
        return ", ".join(self.providers)

    @property
    def suggested_loop_interval_ms(self) -> int:
        return min(stream.loop_interval_ms_suggestion for stream in self.streams)


@dataclass(frozen=True, slots=True)
class ProjectContext:
    working_dir: Path


@dataclass(frozen=True, slots=True)
class ScaffoldPaths:
    project_dir: Path
    package_dir: Path
    pyproject_path: Path
    readme_path: Path
    init_path: Path
    factory_path: Path
    driver_path: Path

    def generated_files(self) -> tuple[Path, ...]:
        return (
            self.pyproject_path,
            self.readme_path,
            self.init_path,
            self.factory_path,
            self.driver_path,
        )
