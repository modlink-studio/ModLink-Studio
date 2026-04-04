"""Filesystem writer for generated plugin scaffolds."""

from __future__ import annotations

import shutil
from pathlib import Path

from ..i18n import Language
from .context import next_step_commands, resolve_scaffold_paths
from .spec import DriverSpec, ProjectContext, ScaffoldPaths
from .templates import (
    generate_driver_py,
    generate_factory_py,
    generate_init_py,
    generate_pyproject_toml,
    generate_readme,
)


def create_plugin_scaffold(
    context: ProjectContext,
    spec: DriverSpec,
    *,
    language: Language = "en",
    overwrite: bool = False,
) -> ScaffoldPaths:
    paths = resolve_scaffold_paths(context, spec)
    _prepare_output_location(paths.project_dir, overwrite=overwrite)
    paths.package_dir.mkdir(parents=True, exist_ok=True)

    file_map: dict[Path, str] = {
        paths.driver_path: generate_driver_py(spec),
        paths.factory_path: generate_factory_py(spec),
        paths.init_path: generate_init_py(spec),
        paths.pyproject_path: generate_pyproject_toml(spec),
        paths.readme_path: generate_readme(spec, next_step_commands(context, spec), language),
    }

    for file_path, content in file_map.items():
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
    return paths


def _prepare_output_location(
    project_dir: Path,
    *,
    overwrite: bool,
) -> None:
    if not project_dir.exists():
        return

    if not overwrite:
        raise FileExistsError(str(project_dir))
    shutil.rmtree(project_dir)
