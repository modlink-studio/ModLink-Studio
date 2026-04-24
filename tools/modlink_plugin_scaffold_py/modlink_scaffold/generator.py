"""File generation logic."""

from __future__ import annotations

import shutil
from pathlib import Path

from .models import DriverSpec, GeneratedProject, Language
from .templates import (
    render_driver_py,
    render_factory_py,
    render_gitignore,
    render_init_py,
    render_license,
    render_pyproject_toml,
    render_readme,
    render_smoke_test,
)


class ScaffoldExistsError(Exception):
    """Raised when target directory already exists."""

    def __init__(self, project_dir: str) -> None:
        super().__init__(f"Target directory already exists: {project_dir}")
        self.project_dir = project_dir


def get_generated_project(spec: DriverSpec, cwd: str) -> GeneratedProject:
    """Get generated project info."""
    project_dir = Path(cwd) / spec.plugin_name
    return GeneratedProject(
        project_dir=str(project_dir),
        written_files=[
            str(project_dir / "pyproject.toml"),
            str(project_dir / "README.md"),
            str(project_dir / "LICENSE"),
            str(project_dir / ".gitignore"),
            str(project_dir / spec.plugin_name / "__init__.py"),
            str(project_dir / spec.plugin_name / "driver.py"),
            str(project_dir / spec.plugin_name / "factory.py"),
            str(project_dir / "tests" / "test_smoke.py"),
        ],
        commands={
            "install": "python -m pip install -e .",
            "test": "python -m pytest",
            "runHost": "python -m modlink_studio",
            "checkEntryPoints": (
                "python -c \"from importlib.metadata import entry_points; "
                "print(sorted(ep.name for ep in entry_points(group='modlink.drivers')))\""
            ),
        },
    )


def write_project_files(
    spec: DriverSpec,
    cwd: str,
    language: Language,
    overwrite: bool = False,
) -> GeneratedProject:
    """Write all project files to disk."""
    generated = get_generated_project(spec, cwd)
    project_dir = Path(generated.project_dir)

    # Check if exists
    if project_dir.exists():
        if not overwrite:
            raise ScaffoldExistsError(str(project_dir))
        shutil.rmtree(project_dir)

    # Create directories
    package_dir = project_dir / spec.plugin_name
    tests_dir = project_dir / "tests"
    package_dir.mkdir(parents=True, exist_ok=True)
    tests_dir.mkdir(parents=True, exist_ok=True)

    # Write files
    files: list[tuple[Path, str]] = [
        (project_dir / "pyproject.toml", render_pyproject_toml(spec)),
        (project_dir / "README.md", render_readme(spec, language)),
        (project_dir / "LICENSE", render_license()),
        (project_dir / ".gitignore", render_gitignore()),
        (package_dir / "__init__.py", render_init_py(spec)),
        (package_dir / "driver.py", render_driver_py(spec)),
        (package_dir / "factory.py", render_factory_py(spec)),
        (tests_dir / "test_smoke.py", render_smoke_test(spec)),
    ]

    for file_path, content in files:
        file_path.write_text(content, encoding="utf-8")

    return generated