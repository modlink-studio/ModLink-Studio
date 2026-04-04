"""Completion screen for the Textual scaffold app."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Label, Static

from ...core.context import NextStepCommands
from ...core.spec import ScaffoldPaths
from ...i18n import Language, t


class CompletionScreen(Screen[None]):
    def __init__(self, language: Language, paths: ScaffoldPaths, commands: NextStepCommands) -> None:
        self.language = language
        self.paths = paths
        self.commands = commands
        super().__init__()

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="completion-layout"):
            yield Label(t(self.language, "complete_title"), classes="section-title")
            yield Static(t(self.language, "complete_created", path=self.paths.project_dir), id="completion-project-dir")
            yield Static(_render_files(self.language, self.paths), id="completion-files")
            yield Static(_render_commands(self.language, self.commands), id="completion-commands")
            with Horizontal(classes="dialog-actions"):
                yield Button(t(self.language, "complete_back"), id="completion-back")
                yield Button(t(self.language, "complete_exit"), id="completion-exit", variant="success")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "completion-back":
            self.app.pop_screen()
            return
        if event.button.id == "completion-exit":
            self.app.exit(0)


def _render_files(language: Language, paths: ScaffoldPaths) -> str:
    files = "\n".join(f"- {path}" for path in paths.generated_files())
    return f"{t(language, 'complete_files')}\n{files}"


def _render_commands(language: Language, commands: NextStepCommands) -> str:
    return "\n".join(
        [
            t(language, "complete_commands"),
            f"- {t(language, 'success_install')}: {commands.install_plugin_from_parent}",
            f"- {t(language, 'success_run_module')}: {commands.run_module}",
            f"- {t(language, 'success_run_script')}: {commands.run_script}",
            f"- {t(language, 'success_check')}: {commands.test}",
        ]
    )
