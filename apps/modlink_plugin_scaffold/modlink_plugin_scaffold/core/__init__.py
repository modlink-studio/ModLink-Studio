"""Core data and generation helpers for the scaffold tool."""

from .context import NextStepCommands, create_project_context, next_step_commands, resolve_scaffold_paths
from .generator import create_plugin_scaffold
from .spec import DriverSpec, ProjectContext, ScaffoldPaths, StreamSpec

__all__ = [
    "DriverSpec",
    "NextStepCommands",
    "ProjectContext",
    "ScaffoldPaths",
    "StreamSpec",
    "create_plugin_scaffold",
    "create_project_context",
    "next_step_commands",
    "resolve_scaffold_paths",
]
