"""Rich render helpers for the full-screen scaffold TUI."""

from __future__ import annotations

from dataclasses import dataclass

from rich.align import Align
from rich.console import Group, RenderableType
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


@dataclass(frozen=True, slots=True)
class ScreenModel:
    title: str
    subtitle: str
    current_title: str
    page_title: str
    draft_title: str
    status_title: str
    current_input: RenderableType
    page_summary: RenderableType
    draft_summary: RenderableType
    status: RenderableType
    footer: str


def render_screen(model: ScreenModel) -> Layout:
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="footer", size=3),
    )
    layout["body"].split_row(
        Layout(name="main", ratio=3),
        Layout(name="side", ratio=2),
    )
    layout["main"].split_column(
        Layout(name="current", size=15),
        Layout(name="page"),
    )
    layout["side"].split_column(
        Layout(name="draft"),
        Layout(name="status", size=12),
    )

    header_text = Text()
    header_text.append(model.title, style="bold cyan")
    header_text.append("  ")
    header_text.append(model.subtitle, style="dim")

    layout["header"].update(Panel(Align.left(header_text), border_style="cyan"))
    layout["current"].update(Panel(model.current_input, title=model.current_title, border_style="green"))
    layout["page"].update(Panel(model.page_summary, title=model.page_title, border_style="blue"))
    layout["draft"].update(Panel(model.draft_summary, title=model.draft_title, border_style="magenta"))
    layout["status"].update(Panel(model.status, title=model.status_title, border_style="yellow"))
    layout["footer"].update(Panel(model.footer, border_style="cyan"))
    return layout


def render_labeled_lines(lines: list[tuple[str, str]], *, highlight_index: int | None = None) -> Table:
    table = Table(box=None, expand=True, padding=(0, 1), show_header=False)
    table.add_column("label", style="cyan", no_wrap=True)
    table.add_column("value", style="white")
    for index, (label, value) in enumerate(lines):
        label_text = Text(label)
        value_text = Text(value)
        if highlight_index is not None and index == highlight_index:
            label_text.stylize("bold yellow")
            value_text.stylize("bold yellow")
        table.add_row(label_text, value_text)
    return table


def render_buffer(value: str, cursor: int) -> Text:
    text = Text()
    if not value:
        text.append(" ", style="reverse")
        return text

    safe_cursor = max(0, min(cursor, len(value)))
    for index, char in enumerate(value):
        if index == safe_cursor:
            text.append(char, style="reverse")
        else:
            text.append(char)
    if safe_cursor == len(value):
        text.append(" ", style="reverse")
    return text


def render_group(*parts: RenderableType) -> Group:
    return Group(*parts)
