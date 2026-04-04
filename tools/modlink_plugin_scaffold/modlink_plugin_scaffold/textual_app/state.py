"""State models for the Textual scaffold application."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from ..core.spec import DataArrivalPattern, DriverKind, PayloadType

PreviewTab = Literal["summary", "driver_py", "pyproject", "readme"]


@dataclass(slots=True)
class StreamDraft:
    modality: str
    display_name: str
    payload_type: PayloadType
    sample_rate_hz: str
    chunk_size: str
    channel_count: str
    channel_names: str
    unit: str
    raster_length: str
    field_height: str
    field_width: str
    video_height: str
    video_width: str


def make_default_stream(index: int) -> StreamDraft:
    label_index = index + 1
    return StreamDraft(
        modality=f"stream_{label_index}",
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


@dataclass(slots=True)
class ScaffoldDraft:
    plugin_name: str = "my-device"
    display_name: str = ""
    device_id: str = ""
    providers_text: str = "serial"
    data_arrival: DataArrivalPattern = "unsure"
    driver_kind: DriverKind = "driver"
    dependencies_text: str = ""
    streams: list[StreamDraft] = field(default_factory=lambda: [make_default_stream(0)])
    selected_stream_index: int = 0
    preview_tab: PreviewTab = "summary"
