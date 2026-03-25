"""CLI entry point for the plugin scaffold application."""

from __future__ import annotations

import argparse
import sys

from rich.console import Console

from .core.context import create_project_context
from .core.generator import create_plugin_scaffold
from .i18n import Language, t
from .tui import prompt_for_driver_spec


def main() -> None:
    language = _parse_language()
    console = Console()

    if not sys.stdin.isatty() or not sys.stdout.isatty():
        Console(stderr=True).print(f"[bold red]{t(language, 'tty_required')}[/bold red]")
        raise SystemExit(2)

    try:
        context = create_project_context()
        spec = prompt_for_driver_spec(console, context, language)
        create_plugin_scaffold(console, context, spec, language)
    except KeyboardInterrupt:
        console.print(f"\n[yellow]{t(language, 'cancelled')}[/yellow]")
        raise SystemExit(0)


def _parse_language() -> Language:
    parser = argparse.ArgumentParser(prog="modlink-plugin-scaffold")
    parser.add_argument("--zh", action="store_true", help="Use the Chinese interface.")
    args = parser.parse_args()
    return "zh" if args.zh else "en"
