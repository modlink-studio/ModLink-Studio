"""Data models for scaffold configuration."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

DriverKind = Literal["driver", "loop"]
DataArrival = Literal["push", "poll", "unsure"]
PayloadType = Literal["signal", "raster", "field", "video"]
Language = Literal["en", "zh"]


class StreamDraft(BaseModel):
    """Draft configuration for a data stream."""

    stream_key: str = Field(default="stream_1", description="Stream identifier")
    display_name: str = Field(default="Stream 1", description="Human-readable name")
    payload_type: PayloadType = Field(default="signal", description="Payload type")
    sample_rate_hz: str = Field(default="250", description="Sample rate in Hz")
    chunk_size: str = Field(default="25", description="Chunk size")
    channel_count: str = Field(default="2", description="Number of channels")
    channel_names: str = Field(default="ch1, ch2", description="Channel names (comma-separated)")
    unit: str = Field(default="", description="Measurement unit")
    raster_length: str = Field(default="128", description="Raster length")
    field_height: str = Field(default="48", description="Field height")
    field_width: str = Field(default="48", description="Field width")
    video_height: str = Field(default="480", description="Video height")
    video_width: str = Field(default="640", description="Video width")


class Draft(BaseModel):
    """Draft configuration for the entire driver plugin."""

    plugin_name: str = Field(default="my-device", description="Plugin package name")
    display_name: str = Field(default="", description="Display name for the driver")
    device_id: str = Field(default="", description="Device identifier")
    providers_text: str = Field(default="serial", description="Providers (comma-separated)")
    data_arrival: DataArrival = Field(default="unsure", description="Data arrival mode")
    driver_kind: DriverKind = Field(default="driver", description="Driver kind")
    dependencies_text: str = Field(default="", description="Additional dependencies")
    streams: list[StreamDraft] = Field(default_factory=lambda: [StreamDraft()], description="Data streams")


class StreamSpec(BaseModel):
    """Validated specification for a data stream."""

    stream_key: str
    display_name: str
    payload_type: PayloadType
    sample_rate_hz: float
    chunk_size: int
    channel_names: list[str]
    unit: str | None = None
    raster_length: int | None = None
    field_height: int | None = None
    field_width: int | None = None
    video_height: int | None = None
    video_width: int | None = None


class DriverSpec(BaseModel):
    """Validated specification for the entire driver plugin."""

    plugin_name: str
    project_name: str
    class_name: str
    display_name: str
    device_id: str
    providers: list[str]
    driver_kind: DriverKind
    driver_reason: str
    data_arrival: DataArrival
    dependencies: list[str]
    streams: list[StreamSpec]


class GeneratedProject(BaseModel):
    """Result of project generation."""

    project_dir: str
    written_files: list[str]
    commands: dict[str, str]


def create_default_stream(index: int) -> StreamDraft:
    """Create a default stream draft with numbered defaults."""
    label_index = index + 1
    return StreamDraft(
        stream_key=f"stream_{label_index}",
        display_name=f"Stream {label_index}",
        payload_type="signal",
        sample_rate_hz="250",
        chunk_size="25",
        channel_count="2",
        channel_names="ch1, ch2",
        unit="",
        raster_length="128",
        field_height="48",
        field_width="48",
        video_height="480",
        video_width="640",
    )


def create_default_draft() -> Draft:
    """Create a default draft with sensible defaults."""
    return Draft(
        plugin_name="my-device",
        display_name="",
        device_id="",
        providers_text="serial",
        data_arrival="unsure",
        driver_kind="driver",
        dependencies_text="",
        streams=[create_default_stream(0)],
    )