"""Preview widgets for the Textual scaffold app."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Button, Label, Static

from ...i18n import Language, t
from ..messages import PreviewTabRequested
from ..state import PreviewTab
from ..services.preview import PreviewBundle


class PreviewPane(Static):
    def __init__(self, language: Language) -> None:
        self.language = language
        super().__init__(id="preview-pane", classes="preview-card")

    def compose(self) -> ComposeResult:
        yield Label(t(self.language, "preview_title"), classes="section-title")
        with Horizontal(id="preview-tab-bar"):
            yield Button(t(self.language, "preview_tab_summary"), id="preview-tab-summary")
            yield Button(t(self.language, "preview_tab_driver"), id="preview-tab-driver")
            yield Button(t(self.language, "preview_tab_pyproject"), id="preview-tab-pyproject")
            yield Button(t(self.language, "preview_tab_readme"), id="preview-tab-readme")
        yield Static("", id="preview-content", classes="preview-content", markup=False)

    def set_preview(self, bundle: PreviewBundle, active_tab: PreviewTab) -> None:
        self.query_one("#preview-content", Static).update(bundle.content_for(active_tab))
        tab_map = {
            "summary": "preview-tab-summary",
            "driver_py": "preview-tab-driver",
            "pyproject": "preview-tab-pyproject",
            "readme": "preview-tab-readme",
        }
        active_id = tab_map[active_tab]
        for button_id in tab_map.values():
            button = self.query_one(f"#{button_id}", Button)
            if button_id == active_id:
                button.add_class("active-tab")
            else:
                button.remove_class("active-tab")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id or ""
        tab_map: dict[str, PreviewTab] = {
            "preview-tab-summary": "summary",
            "preview-tab-driver": "driver_py",
            "preview-tab-pyproject": "pyproject",
            "preview-tab-readme": "readme",
        }
        tab = tab_map.get(button_id)
        if tab is not None:
            self.post_message(PreviewTabRequested(tab))
