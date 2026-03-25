"""Filesystem writer for generated plugin scaffolds."""

from __future__ import annotations

import shutil
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

from ..i18n import Language, t
from .context import next_step_commands, resolve_scaffold_paths
from .spec import DriverSpec, ProjectContext
from .templates import (
    generate_driver_py,
    generate_factory_py,
    generate_init_py,
    generate_pyproject_toml,
    generate_readme,
)


def create_plugin_scaffold(
    console: Console,
    context: ProjectContext,
    spec: DriverSpec,
    language: Language = "en",
) -> None:
    paths = resolve_scaffold_paths(context, spec)
    commands = next_step_commands(context, spec)

    _prepare_output_location(console, context, paths.project_dir, language)
    paths.package_dir.mkdir(parents=True, exist_ok=True)

    file_map: dict[Path, str] = {
        paths.driver_path: generate_driver_py(spec),
        paths.factory_path: generate_factory_py(spec),
        paths.init_path: generate_init_py(spec),
        paths.pyproject_path: generate_pyproject_toml(spec),
        paths.readme_path: generate_readme(spec, commands, language),
    }

    console.print("")
    console.print(f"[bold cyan]{t(language, 'creating_scaffold')}[/bold cyan] [cyan]{paths.project_dir}[/cyan]")
    console.print("")

    for file_path, content in file_map.items():
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        console.print(f"[green]{t(language, 'created_label')}[/green] [dim]{_display_path(context, file_path)}[/dim]")

    console.print("")
    console.print(
        Panel(
            "[bold green]{created}[/bold green]\n\n"
            "{install}:\n[cyan]{install_cmd}[/cyan]\n\n"
            "{run_module}:\n[cyan]{run_module_cmd}[/cyan]\n\n"
            "{run_script}:\n[cyan]{run_script_cmd}[/cyan]\n\n"
            "{check}:\n[cyan]{check_cmd}[/cyan]\n\n"
            "{repeat}".format(
                created=t(language, "success_created"),
                install=t(language, "success_install"),
                install_cmd=commands.install_plugin_from_parent,
                run_module=t(language, "success_run_module"),
                run_module_cmd=commands.run_module,
                run_script=t(language, "success_run_script"),
                run_script_cmd=commands.run_script,
                check=t(language, "success_check"),
                check_cmd=commands.test,
                repeat=t(language, "success_repeat"),
            ),
            title=f"[bold green]{t(language, 'success_title')}[/bold green]",
            border_style="green",
            padding=(1, 2),
        )
    )


def _prepare_output_location(
    console: Console,
    context: ProjectContext,
    project_dir: Path,
    language: Language,
) -> None:
    if not project_dir.exists():
        return

    if not Confirm.ask(
        f"[yellow]{t(language, 'overwrite_prompt', name=project_dir.relative_to(context.working_dir))}[/yellow]",
        default=False,
        console=console,
    ):
        console.print(f"[yellow]{t(language, 'overwrite_cancelled')}[/yellow]")
        raise SystemExit(0)
    shutil.rmtree(project_dir)


def _display_path(context: ProjectContext, file_path: Path) -> str:
    try:
        return str(file_path.relative_to(context.working_dir))
    except ValueError:
        return str(file_path)
