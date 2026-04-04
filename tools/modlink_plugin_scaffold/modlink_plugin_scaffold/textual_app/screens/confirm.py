"""Confirm screens for the Textual scaffold app."""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static

from ...i18n import Language, t


class ConfirmOverwriteScreen(ModalScreen[bool]):
    def __init__(self, language: Language, project_dir: Path) -> None:
        self.language = language
        self.project_dir = project_dir
        super().__init__()

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-dialog"):
            yield Label(t(self.language, "confirm_overwrite_title"), classes="dialog-title")
            yield Static(
                t(self.language, "confirm_overwrite_body", path=self.project_dir),
                id="confirm-overwrite-message",
            )
            with Horizontal(classes="dialog-actions"):
                yield Button(t(self.language, "confirm_overwrite_cancel"), id="cancel-overwrite")
                yield Button(t(self.language, "confirm_overwrite_confirm"), id="confirm-overwrite", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "confirm-overwrite")
