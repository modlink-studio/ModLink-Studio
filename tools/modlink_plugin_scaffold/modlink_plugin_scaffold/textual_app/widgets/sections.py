"""Form sections for the Textual scaffold app."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Input, Label, Select, Static

from ...i18n import DATA_ARRIVAL_CHOICES, Language, t
from ..state import ScaffoldDraft, StreamDraft


def _field_row(*children, row_id: str) -> Container:
    return Container(*children, id=row_id, classes="field-row")


class IdentitySection(Static):
    def __init__(self, language: Language) -> None:
        self.language = language
        super().__init__(id="identity-section", classes="section-card")

    def compose(self) -> ComposeResult:
        yield Label(t(self.language, "step_identity"), classes="section-title")
        yield Static(t(self.language, "identity_hint"), classes="section-hint")
        yield _field_row(
            Label(t(self.language, "plugin_name_label")),
            Input(id="plugin-name-input"),
            row_id="row-plugin-name",
        )
        yield _field_row(
            Label(t(self.language, "display_name_label")),
            Input(id="display-name-input"),
            row_id="row-display-name",
        )
        yield _field_row(
            Label(t(self.language, "device_id_label")),
            Input(id="device-id-input"),
            row_id="row-device-id",
        )

    def set_values(self, draft: ScaffoldDraft) -> None:
        self._set_input_value("plugin-name-input", draft.plugin_name)
        self._set_input_value("display-name-input", draft.display_name)
        self._set_input_value("device-id-input", draft.device_id)

    def _set_input_value(self, widget_id: str, value: str) -> None:
        widget = self.query_one(f"#{widget_id}", Input)
        if widget.value != value:
            widget.value = value


class ConnectionSection(Static):
    def __init__(self, language: Language) -> None:
        self.language = language
        super().__init__(id="connection-section", classes="section-card")

    def compose(self) -> ComposeResult:
        yield Label(t(self.language, "step_connection"), classes="section-title")
        yield Static(t(self.language, "connection_hint"), classes="section-hint")
        yield _field_row(
            Label(t(self.language, "providers_label")),
            Input(id="providers-input"),
            row_id="row-providers",
        )

    def set_values(self, draft: ScaffoldDraft) -> None:
        widget = self.query_one("#providers-input", Input)
        if widget.value != draft.providers_text:
            widget.value = draft.providers_text


class DriverTypeSection(Static):
    def __init__(self, language: Language) -> None:
        self.language = language
        super().__init__(id="driver-type-section", classes="section-card")

    def compose(self) -> ComposeResult:
        data_arrival_options = [(choice.key, choice.key) for choice in DATA_ARRIVAL_CHOICES]
        driver_kind_options = [("driver", "driver"), ("loop", "loop")]
        yield Label(t(self.language, "step_driver_type"), classes="section-title")
        yield Static(t(self.language, "driver_type_hint_3"), classes="section-hint")
        yield _field_row(
            Label(t(self.language, "data_arrival_label")),
            Select(data_arrival_options, id="data-arrival-select", allow_blank=False),
            row_id="row-data-arrival",
        )
        yield _field_row(
            Label(t(self.language, "base_class_label")),
            Select(driver_kind_options, id="driver-kind-select", allow_blank=False),
            row_id="row-driver-kind",
        )
        yield Static(id="driver-recommendation", classes="recommendation-box")

    def set_values(self, draft: ScaffoldDraft, recommended_label: str, recommended_reason: str) -> None:
        data_arrival = self.query_one("#data-arrival-select", Select)
        driver_kind = self.query_one("#driver-kind-select", Select)
        if data_arrival.value != draft.data_arrival:
            data_arrival.value = draft.data_arrival
        if driver_kind.value != draft.driver_kind:
            driver_kind.value = draft.driver_kind
        self.query_one("#driver-recommendation", Static).update(
            f"{t(self.language, 'recommended_base')}: {recommended_label}\n{recommended_reason}"
        )


class DependenciesSection(Static):
    def __init__(self, language: Language) -> None:
        self.language = language
        super().__init__(id="dependencies-section", classes="section-card")

    def compose(self) -> ComposeResult:
        yield Label(t(self.language, "step_dependencies"), classes="section-title")
        yield Static(t(self.language, "dependencies_hint"), classes="section-hint")
        yield _field_row(
            Label(t(self.language, "extra_dependencies_label")),
            Input(id="dependencies-input"),
            row_id="row-dependencies",
        )

    def set_values(self, draft: ScaffoldDraft) -> None:
        widget = self.query_one("#dependencies-input", Input)
        if widget.value != draft.dependencies_text:
            widget.value = draft.dependencies_text


class StreamDetailSection(Static):
    def __init__(self, language: Language) -> None:
        self.language = language
        super().__init__(id="stream-detail-section", classes="stream-detail")

    def compose(self) -> ComposeResult:
        yield Label(t(self.language, "stream_detail_title"), classes="section-title", id="stream-detail-heading")
        yield Static(t(self.language, "stream_panel_hint"), classes="section-hint")
        yield _field_row(Label(t(self.language, "modality_label")), Input(id="stream-modality-input"), row_id="row-stream-modality")
        yield _field_row(Label(t(self.language, "stream_display_name_label")), Input(id="stream-display-name-input"), row_id="row-stream-display-name")
        yield _field_row(
            Label(t(self.language, "payload_type_label")),
            Select(
                list(DATA_PAYLOAD_OPTIONS),
                id="stream-payload-select",
                allow_blank=False,
            ),
            row_id="row-stream-payload",
        )
        yield _field_row(Label(t(self.language, "sample_rate_label")), Input(id="stream-sample-rate-input"), row_id="row-stream-sample-rate")
        yield _field_row(Label(t(self.language, "chunk_size_label")), Input(id="stream-chunk-size-input"), row_id="row-stream-chunk-size")
        yield _field_row(Label(t(self.language, "channel_count_label")), Input(id="stream-channel-count-input"), row_id="row-stream-channel-count")
        yield _field_row(Label(t(self.language, "channel_names_label")), Input(id="stream-channel-names-input"), row_id="row-stream-channel-names")
        yield _field_row(Label(t(self.language, "unit_label")), Input(id="stream-unit-input"), row_id="row-stream-unit")
        yield _field_row(Label(t(self.language, "raster_length_label")), Input(id="stream-raster-length-input"), row_id="row-stream-raster-length")
        yield _field_row(Label(t(self.language, "field_height_label")), Input(id="stream-field-height-input"), row_id="row-stream-field-height")
        yield _field_row(Label(t(self.language, "field_width_label")), Input(id="stream-field-width-input"), row_id="row-stream-field-width")
        yield _field_row(Label(t(self.language, "frame_height_label")), Input(id="stream-video-height-input"), row_id="row-stream-video-height")
        yield _field_row(Label(t(self.language, "frame_width_label")), Input(id="stream-video-width-input"), row_id="row-stream-video-width")

    def set_stream(self, stream: StreamDraft, index: int) -> None:
        self.query_one("#stream-detail-heading", Label).update(
            f"{t(self.language, 'stream_detail_title')} #{index + 1}"
        )
        self._set_input_value("stream-modality-input", stream.modality)
        self._set_input_value("stream-display-name-input", stream.display_name)
        payload_widget = self.query_one("#stream-payload-select", Select)
        if payload_widget.value != stream.payload_type:
            payload_widget.value = stream.payload_type
        self._set_input_value("stream-sample-rate-input", stream.sample_rate_hz)
        self._set_input_value("stream-chunk-size-input", stream.chunk_size)
        self._set_input_value("stream-channel-count-input", stream.channel_count)
        self._set_input_value("stream-channel-names-input", stream.channel_names)
        self._set_input_value("stream-unit-input", stream.unit)
        self._set_input_value("stream-raster-length-input", stream.raster_length)
        self._set_input_value("stream-field-height-input", stream.field_height)
        self._set_input_value("stream-field-width-input", stream.field_width)
        self._set_input_value("stream-video-height-input", stream.video_height)
        self._set_input_value("stream-video-width-input", stream.video_width)
        self.set_payload_visibility(stream.payload_type)

    def set_payload_visibility(self, payload_type: str) -> None:
        visibility_map = {
            "row-stream-channel-count": payload_type == "signal",
            "row-stream-channel-names": True,
            "row-stream-unit": payload_type in {"signal", "raster", "field"},
            "row-stream-raster-length": payload_type == "raster",
            "row-stream-field-height": payload_type == "field",
            "row-stream-field-width": payload_type == "field",
            "row-stream-video-height": payload_type == "video",
            "row-stream-video-width": payload_type == "video",
        }
        for row_id, visible in visibility_map.items():
            self.query_one(f"#{row_id}", Container).display = visible

    def _set_input_value(self, widget_id: str, value: str) -> None:
        widget = self.query_one(f"#{widget_id}", Input)
        if widget.value != value:
            widget.value = value


DATA_PAYLOAD_OPTIONS = (
    ("signal", "signal"),
    ("raster", "raster"),
    ("field", "field"),
    ("video", "video"),
)
