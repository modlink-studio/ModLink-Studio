"""State containers for the full-screen scaffold TUI."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Literal

from ..core.spec import DriverSpec, ProjectContext
from ..i18n import Language

StepId = Literal["identity", "connection", "driver_type", "streams", "dependencies", "summary"]
FieldId = str


@dataclass(slots=True)
class StreamDraft:
    modality: str
    display_name: str
    payload_type: str
    sample_rate_hz: float
    chunk_size: int
    channel_count: int
    channel_names: tuple[str, ...]
    unit: str
    raster_length: int
    field_height: int
    field_width: int
    video_height: int
    video_width: int


def make_default_stream(index: int) -> StreamDraft:
    return StreamDraft(
        modality=f"stream_{index + 1}",
        display_name=f"Stream {index + 1}",
        payload_type="signal",
        sample_rate_hz=250.0,
        chunk_size=25,
        channel_count=2,
        channel_names=("ch1", "ch2"),
        unit="",
        raster_length=128,
        field_height=48,
        field_width=48,
        video_height=480,
        video_width=640,
    )


@dataclass(slots=True)
class WizardDraft:
    plugin_name: str = "my-device"
    display_name: str = ""
    device_id: str = ""
    providers: tuple[str, ...] = ("serial",)
    data_arrival: str = "unsure"
    driver_kind: str = "driver"
    driver_reason: str = ""
    stream_count: int = 1
    streams: list[StreamDraft] = field(default_factory=lambda: [make_default_stream(0)])
    dependencies: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CursorState:
    step: StepId = "identity"
    field_index: int = 0
    summary_index: int = 0


@dataclass(slots=True)
class HistoryEntry:
    cursor: CursorState
    draft: WizardDraft


@dataclass(slots=True)
class WizardState:
    context: ProjectContext
    language: Language
    draft: WizardDraft = field(default_factory=WizardDraft)
    cursor: CursorState = field(default_factory=CursorState)
    buffer: str = ""
    buffer_cursor: int = 0
    error: str = ""
    finished_spec: DriverSpec | None = None
    history: list[HistoryEntry] = field(default_factory=list)

    def push_history(self) -> None:
        self.history.append(
            HistoryEntry(
                cursor=CursorState(
                    step=self.cursor.step,
                    field_index=self.cursor.field_index,
                    summary_index=self.cursor.summary_index,
                ),
                draft=deepcopy(self.draft),
            )
        )

    def pop_history(self) -> bool:
        if not self.history:
            return False
        entry = self.history.pop()
        self.cursor = entry.cursor
        self.draft = entry.draft
        return True
