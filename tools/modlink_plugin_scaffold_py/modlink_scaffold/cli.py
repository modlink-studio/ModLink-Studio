"""CLI entry point for scaffold tool."""

from __future__ import annotations

import sys
from pathlib import Path

import typer
from rich.console import Console

from .generator import ScaffoldExistsError, write_project_files
from .i18n import Language
from .models import Draft
from .prompts import prompt_scaffold, show_result
from .validation import validate_draft

app = typer.Typer(
    name="modlink-plugin-scaffold",
    help="Interactive scaffold generator for ModLink Python driver plugins",
)
console = Console()


@app.command()
def scaffold(
    zh: bool = typer.Option(False, "--zh", help="使用中文交互"),
    cwd: str = typer.Option(".", "--cwd", "-d", help="输出目录"),
) -> None:
    """Generate a ModLink Python driver plugin scaffold."""
    language: Language = "zh" if zh else "en"

    # Check TTY
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        console.print("[red]Error:[/red] This tool requires an interactive terminal.")
        raise typer.Exit(1)

    # Resolve cwd
    output_dir = Path(cwd).resolve()

    # Run prompts
    draft = prompt_scaffold(language, str(output_dir))

    if draft is None:
        raise typer.Exit(0)

    # Validate
    validation = validate_draft(language, draft)

    if validation.spec is None:
        console.print("[red]Validation errors:[/red]")
        for field, error in validation.field_errors.items():
            console.print(f"  • {field}: {error}")
        raise typer.Exit(1)

    # Handle existing directory
    try:
        result = write_project_files(validation.spec, str(output_dir), language, overwrite=False)
        show_result(result, language)
    except ScaffoldExistsError as e:
        from rich.prompt import Confirm

        copy = {
            "zh": {"overwrite_prompt": "目录已存在。是否覆盖？"},
            "en": {"overwrite_prompt": "Directory exists. Overwrite?"},
        }
        lang_copy = copy.get(language, copy["en"])

        if Confirm.ask(lang_copy["overwrite_prompt"], default=False):
            result = write_project_files(validation.spec, str(output_dir), language, overwrite=True)
            show_result(result, language)
        else:
            console.print("[yellow]Cancelled[/yellow]")
            raise typer.Exit(0)


def main(argv: list[str] | None = None) -> int:
    """Main entry point for script invocation."""
    try:
        app(argv if argv is not None else sys.argv[1:])
        return 0
    except typer.Exit as e:
        return e.exit_code


if __name__ == "__main__":
    raise SystemExit(main())