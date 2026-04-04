"""Textual application for the plugin scaffold tool."""

from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.css.query import NoMatches
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Footer, Header, Input, Select, Static

from ..core.context import create_project_context
from ..core.generator import create_plugin_scaffold
from ..i18n import Language, t
from .messages import PreviewTabRequested, StreamActionRequested, StreamSelected
from .screens import CompletionScreen, ConfirmOverwriteScreen
from .services import (
    add_stream,
    build_preview_bundle,
    describe_generation,
    move_stream_down,
    move_stream_up,
    duplicate_stream,
    delete_stream,
    select_stream,
    set_data_arrival,
    set_dependencies_text,
    set_device_id,
    set_display_name,
    set_driver_kind,
    set_plugin_name,
    set_preview_tab,
    set_providers_text,
    set_stream_field,
)
from .state import PreviewTab, ScaffoldDraft
from .widgets import ConnectionSection, DependenciesSection, DriverTypeSection, IdentitySection, PreviewPane, StreamsSection


class ScaffoldTextualApp(App[int | None]):
    """Interactive scaffold generator built with Textual."""

    CSS_PATH = "styles.tcss"
    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("f5", "generate", "Generate"),
    ]

    def __init__(self, *, language: Language = "en", working_dir: Path | None = None) -> None:
        self.language = language
        self.context = create_project_context(working_dir)
        self.draft = ScaffoldDraft()
        self._syncing_ui = False
        self._ui_ready = False
        self._pending_spec = None
        self._preview_bundle = None
        super().__init__()
        self.title = t(language, "wizard_title")
        self.sub_title = str(self.context.working_dir)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Horizontal(id="body"):
            with VerticalScroll(id="editor-column"):
                yield IdentitySection(self.language)
                yield ConnectionSection(self.language)
                yield DriverTypeSection(self.language)
                yield StreamsSection(self.language)
                yield DependenciesSection(self.language)
            with Vertical(id="preview-column"):
                yield PreviewPane(self.language)
                yield Static(id="validation-banner")
                yield Button(t(self.language, "generate_button"), id="generate-button", variant="success")
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_view()
        self._ui_ready = True

    def action_generate(self) -> None:
        self._generate_if_possible()

    def on_input_changed(self, event: Input.Changed) -> None:
        if self._syncing_ui or not self._ui_ready:
            return
        self._apply_input_change(event.input.id or "", event.value)

    def on_select_changed(self, event: Select.Changed) -> None:
        if self._syncing_ui or not self._ui_ready:
            return
        self._apply_select_change(event.select.id or "", str(event.value))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "generate-button":
            self._generate_if_possible()

    def on_stream_selected(self, message: StreamSelected) -> None:
        if self._syncing_ui or not self._ui_ready:
            return
        if message.index == self.draft.selected_stream_index:
            return
        select_stream(self.draft, message.index)
        self._refresh_view()

    def on_stream_action_requested(self, message: StreamActionRequested) -> None:
        if not self._ui_ready:
            return
        action = message.action
        if action == "add":
            add_stream(self.draft)
        elif action == "duplicate":
            duplicate_stream(self.draft)
        elif action == "delete":
            delete_stream(self.draft)
        elif action == "up":
            move_stream_up(self.draft)
        elif action == "down":
            move_stream_down(self.draft)
        self._refresh_view()

    def on_preview_tab_requested(self, message: PreviewTabRequested) -> None:
        set_preview_tab(self.draft, message.tab)
        self._refresh_view()

    def set_input_value(self, widget_id: str, value: str) -> None:
        widget = self.query_one(f"#{widget_id}", Input)
        widget.value = value
        self._apply_input_change(widget_id, value)

    def set_select_value(self, widget_id: str, value: str) -> None:
        widget = self.query_one(f"#{widget_id}", Select)
        widget.value = value
        self._apply_select_change(widget_id, value)

    def click_stream_action(self, action: str) -> None:
        self.on_stream_action_requested(StreamActionRequested(action))

    def choose_stream(self, index: int) -> None:
        self.on_stream_selected(StreamSelected(index))

    def activate_preview_tab(self, tab: PreviewTab) -> None:
        self.on_preview_tab_requested(PreviewTabRequested(tab))

    def _refresh_view(self) -> None:
        bundle = build_preview_bundle(self.context, self.language, self.draft)
        self._preview_bundle = bundle

        try:
            self.query_one("#identity-section")
        except NoMatches:
            return

        self._syncing_ui = True
        try:
            self.query_one(IdentitySection).set_values(self.draft)
            self.query_one(ConnectionSection).set_values(self.draft)
            self.query_one(DriverTypeSection).set_values(
                self.draft,
                _base_class_name(self.language, bundle.validation.recommended_driver_kind),
                bundle.validation.recommended_reason,
            )
            self.query_one(DependenciesSection).set_values(self.draft)
            streams_section = self.query_one(StreamsSection)
            streams_section.query_one("#stream-list-panel").set_streams(
                self.draft.streams,
                self.draft.selected_stream_index,
                _error_indexes(bundle.validation.field_errors),
            )
            streams_section.query_one("#stream-detail-section").set_stream(
                self.draft.streams[self.draft.selected_stream_index],
                self.draft.selected_stream_index,
            )
            self.query_one(PreviewPane).set_preview(bundle, self.draft.preview_tab)
            self._update_validation_banner(bundle.validation.first_error, bundle.validation.can_generate)
            generate_button = self.query_one("#generate-button", Button)
            generate_button.disabled = not bundle.validation.can_generate
            self._apply_invalid_styles(bundle.validation.field_errors)
        finally:
            self._syncing_ui = False

    def _update_validation_banner(self, error: str, can_generate: bool) -> None:
        banner = self.query_one("#validation-banner", Static)
        banner.remove_class("error")
        banner.remove_class("ok")
        if error:
            banner.update(f"{t(self.language, 'validation_error_prefix')} {error}")
            banner.add_class("error")
            return
        banner.update(t(self.language, "validation_ok"))
        banner.add_class("ok" if can_generate else "error")

    def _apply_invalid_styles(self, field_errors: dict[str, str]) -> None:
        widget_ids = [
            "plugin-name-input",
            "display-name-input",
            "device-id-input",
            "providers-input",
            "data-arrival-select",
            "driver-kind-select",
            "dependencies-input",
            "stream-modality-input",
            "stream-display-name-input",
            "stream-payload-select",
            "stream-sample-rate-input",
            "stream-chunk-size-input",
            "stream-channel-count-input",
            "stream-channel-names-input",
            "stream-unit-input",
            "stream-raster-length-input",
            "stream-field-height-input",
            "stream-field-width-input",
            "stream-video-height-input",
            "stream-video-width-input",
        ]
        for widget_id in widget_ids:
            widget = self.query_one(f"#{widget_id}")
            widget.remove_class("invalid")

        selected_prefix = f"stream.{self.draft.selected_stream_index}."
        field_to_widget = {
            "plugin_name": "plugin-name-input",
            "display_name": "display-name-input",
            "device_id": "device-id-input",
            "providers": "providers-input",
            "data_arrival": "data-arrival-select",
            "driver_kind": "driver-kind-select",
            "dependencies": "dependencies-input",
            f"{selected_prefix}modality": "stream-modality-input",
            f"{selected_prefix}display_name": "stream-display-name-input",
            f"{selected_prefix}payload_type": "stream-payload-select",
            f"{selected_prefix}sample_rate_hz": "stream-sample-rate-input",
            f"{selected_prefix}chunk_size": "stream-chunk-size-input",
            f"{selected_prefix}channel_count": "stream-channel-count-input",
            f"{selected_prefix}channel_names": "stream-channel-names-input",
            f"{selected_prefix}unit": "stream-unit-input",
            f"{selected_prefix}raster_length": "stream-raster-length-input",
            f"{selected_prefix}field_height": "stream-field-height-input",
            f"{selected_prefix}field_width": "stream-field-width-input",
            f"{selected_prefix}video_height": "stream-video-height-input",
            f"{selected_prefix}video_width": "stream-video-width-input",
        }
        for field_id in field_errors:
            widget_id = field_to_widget.get(field_id)
            if widget_id is not None:
                self.query_one(f"#{widget_id}").add_class("invalid")

    def _generate_if_possible(self) -> None:
        if self._preview_bundle is None or self._preview_bundle.validation.spec is None:
            return
        self._pending_spec = self._preview_bundle.validation.spec
        details = describe_generation(self.context, self._pending_spec)
        if details.paths.project_dir.exists():
            self.push_screen(
                ConfirmOverwriteScreen(self.language, details.paths.project_dir),
                self._handle_overwrite_confirmation,
            )
            return
        self._complete_generation(overwrite=False)

    def _handle_overwrite_confirmation(self, confirmed: bool | None) -> None:
        if confirmed:
            self._complete_generation(overwrite=True)

    def _complete_generation(self, *, overwrite: bool) -> None:
        if self._pending_spec is None:
            return
        paths = create_plugin_scaffold(
            self.context,
            self._pending_spec,
            language=self.language,
            overwrite=overwrite,
        )
        details = describe_generation(self.context, self._pending_spec)
        self.push_screen(CompletionScreen(self.language, paths, details.commands))

    def _apply_input_change(self, widget_id: str, value: str) -> None:
        if widget_id == "plugin-name-input":
            set_plugin_name(self.draft, value)
        elif widget_id == "display-name-input":
            set_display_name(self.draft, value)
        elif widget_id == "device-id-input":
            set_device_id(self.draft, value)
        elif widget_id == "providers-input":
            set_providers_text(self.draft, value)
        elif widget_id == "dependencies-input":
            set_dependencies_text(self.draft, value)
        else:
            stream_field = _stream_field_name_for_widget(widget_id)
            if stream_field is not None:
                set_stream_field(self.draft, self.draft.selected_stream_index, stream_field, value)
        self._refresh_view()

    def _apply_select_change(self, widget_id: str, value: str) -> None:
        if widget_id == "data-arrival-select":
            set_data_arrival(self.draft, value)
        elif widget_id == "driver-kind-select":
            set_driver_kind(self.draft, value)
        elif widget_id == "stream-payload-select":
            set_stream_field(self.draft, self.draft.selected_stream_index, "payload_type", value)
        self._refresh_view()


def _stream_field_name_for_widget(widget_id: str) -> str | None:
    mapping = {
        "stream-modality-input": "modality",
        "stream-display-name-input": "display_name",
        "stream-sample-rate-input": "sample_rate_hz",
        "stream-chunk-size-input": "chunk_size",
        "stream-channel-count-input": "channel_count",
        "stream-channel-names-input": "channel_names",
        "stream-unit-input": "unit",
        "stream-raster-length-input": "raster_length",
        "stream-field-height-input": "field_height",
        "stream-field-width-input": "field_width",
        "stream-video-height-input": "video_height",
        "stream-video-width-input": "video_width",
    }
    return mapping.get(widget_id)


def _error_indexes(field_errors: dict[str, str]) -> set[int]:
    result: set[int] = set()
    for field_id in field_errors:
        if not field_id.startswith("stream."):
            continue
        _, index, _ = field_id.split(".", 2)
        result.add(int(index))
    return result


def _base_class_name(language: Language, driver_kind: str) -> str:
    return t(language, "base_loop_name") if driver_kind == "loop" else t(language, "base_driver_name")
