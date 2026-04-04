"""Path and command helpers for the scaffold app."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .spec import DriverSpec, ProjectContext, ScaffoldPaths


@dataclass(frozen=True, slots=True)
class NextStepCommands:
    install_plugin_from_parent: str
    install_plugin_in_project: str
    run_module: str
    run_script: str
    test: str


def create_project_context(start: Path | None = None) -> ProjectContext:
    working_dir = Path.cwd() if start is None else Path(start)
    return ProjectContext(working_dir=working_dir.resolve())


def resolve_scaffold_paths(context: ProjectContext, spec: DriverSpec) -> ScaffoldPaths:
    project_dir = context.working_dir / spec.plugin_name
    package_dir = project_dir / spec.plugin_name
    return ScaffoldPaths(
        project_dir=project_dir,
        package_dir=package_dir,
        pyproject_path=project_dir / "pyproject.toml",
        readme_path=project_dir / "README.md",
        init_path=package_dir / "__init__.py",
        factory_path=package_dir / "factory.py",
        driver_path=package_dir / "driver.py",
    )


def next_step_commands(context: ProjectContext, spec: DriverSpec) -> NextStepCommands:
    del context

    entrypoint_probe = (
        'python -c "from importlib.metadata import entry_points; '
        "print(sorted(ep.name for ep in entry_points(group='modlink.drivers')))\""
    )

    return NextStepCommands(
        install_plugin_from_parent=f"python -m pip install -e ./{spec.plugin_name}",
        install_plugin_in_project="python -m pip install -e .",
        run_module="python -m modlink_studio",
        run_script="modlink-studio",
        test=entrypoint_probe,
    )
