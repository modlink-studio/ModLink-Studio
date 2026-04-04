"""CLI entry point for the plugin scaffold application."""

from __future__ import annotations

import argparse
import sys

from .i18n import Language, t
from .textual_app import ScaffoldTextualApp


def main() -> None:
    language = _parse_language()

    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print(t(language, "tty_required"), file=sys.stderr)
        raise SystemExit(2)

    try:
        app = ScaffoldTextualApp(language=language)
        result = app.run()
        raise SystemExit(0 if result is None else int(result))
    except KeyboardInterrupt:
        print(t(language, "cancelled"))
        raise SystemExit(0)


def _parse_language() -> Language:
    parser = argparse.ArgumentParser(prog="modlink-plugin-scaffold")
    parser.add_argument("--zh", action="store_true", help="Use the Chinese interface.")
    args = parser.parse_args()
    return "zh" if args.zh else "en"
