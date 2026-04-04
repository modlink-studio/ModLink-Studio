"""Output helpers for the Textual scaffold app."""

from __future__ import annotations

from dataclasses import dataclass

from ...core.context import NextStepCommands, next_step_commands, resolve_scaffold_paths
from ...core.spec import DriverSpec, ProjectContext, ScaffoldPaths


@dataclass(frozen=True, slots=True)
class GenerationDetails:
    paths: ScaffoldPaths
    commands: NextStepCommands


def describe_generation(context: ProjectContext, spec: DriverSpec) -> GenerationDetails:
    return GenerationDetails(
        paths=resolve_scaffold_paths(context, spec),
        commands=next_step_commands(context, spec),
    )


def project_exists(context: ProjectContext, spec: DriverSpec) -> bool:
    return describe_generation(context, spec).paths.project_dir.exists()
