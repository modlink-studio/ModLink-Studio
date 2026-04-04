"""Stream widgets for the Textual scaffold app."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Button, Label, OptionList, Static

from ...i18n import Language, t
from ...core.spec import to_title_words
from ..messages import StreamActionRequested, StreamSelected
from ..state import StreamDraft
from .sections import StreamDetailSection


class StreamListPanel(Static):
    def __init__(self, language: Language) -> None:
        self.language = language
        self._syncing_options = False
        super().__init__(id="stream-list-panel", classes="stream-list")

    def compose(self) -> ComposeResult:
        yield Label(t(self.language, "stream_list_title"), classes="section-title")
        yield OptionList(id="stream-option-list")
        with Horizontal(classes="stream-actions"):
            yield Button(t(self.language, "action_add_stream"), id="add-stream")
            yield Button(t(self.language, "action_duplicate_stream"), id="duplicate-stream")
            yield Button(t(self.language, "action_delete_stream"), id="delete-stream")
        with Horizontal(classes="stream-actions"):
            yield Button(t(self.language, "action_move_up"), id="move-stream-up")
            yield Button(t(self.language, "action_move_down"), id="move-stream-down")

    def set_streams(
        self,
        streams: list[StreamDraft],
        selected_index: int,
        error_indexes: set[int],
    ) -> None:
        option_list = self.query_one("#stream-option-list", OptionList)
        options: list[str] = []
        for index, stream in enumerate(streams):
            prefix = "!" if index in error_indexes else " "
            display_name = stream.display_name.strip() or f"{to_title_words(stream.modality)} Stream"
            options.append(f"{prefix} {index + 1}. {display_name} [{stream.payload_type}]")
        self._syncing_options = True
        try:
            option_list.set_options(options)
            option_list.highlighted = selected_index if options else None
        finally:
            self._syncing_options = False

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id or ""
        action_map = {
            "add-stream": "add",
            "duplicate-stream": "duplicate",
            "delete-stream": "delete",
            "move-stream-up": "up",
            "move-stream-down": "down",
        }
        action = action_map.get(button_id)
        if action is not None:
            self.post_message(StreamActionRequested(action))

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if self._syncing_options:
            return
        self.post_message(StreamSelected(event.option_index))


class StreamsSection(Static):
    def __init__(self, language: Language) -> None:
        self.language = language
        super().__init__(id="streams-section", classes="section-card")

    def compose(self) -> ComposeResult:
        yield Label(t(self.language, "step_streams"), classes="section-title")
        yield Static(t(self.language, "streams_hint_1"), classes="section-hint")
        yield Container(
            StreamListPanel(self.language),
            StreamDetailSection(self.language),
            id="streams-layout",
        )
