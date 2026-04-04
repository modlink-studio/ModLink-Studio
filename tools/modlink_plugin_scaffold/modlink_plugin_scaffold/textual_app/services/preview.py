"""Preview builders for the Textual scaffold app."""

from __future__ import annotations

from dataclasses import dataclass

from ...core.context import NextStepCommands, resolve_scaffold_paths, next_step_commands
from ...core.spec import DriverSpec, ProjectContext, to_pascal_case, sanitize_identifier
from ...core.templates import generate_driver_py, generate_pyproject_toml, generate_readme
from ...i18n import Language, t
from ..state import PreviewTab, ScaffoldDraft
from .draft_logic import DraftValidation, validate_draft


@dataclass(frozen=True, slots=True)
class PreviewBundle:
    validation: DraftValidation
    summary: str
    driver_py: str
    pyproject_toml: str
    readme: str
    commands: NextStepCommands | None
    project_dir: str

    def content_for(self, tab: PreviewTab) -> str:
        if tab == "summary":
            return self.summary
        if tab == "driver_py":
            return self.driver_py
        if tab == "pyproject":
            return self.pyproject_toml
        return self.readme


def build_preview_bundle(
    context: ProjectContext,
    language: Language,
    draft: ScaffoldDraft,
) -> PreviewBundle:
    validation = validate_draft(language, draft)

    if validation.spec is None:
        summary = _render_invalid_summary(context, language, draft, validation)
        placeholder = t(language, "preview_invalid_placeholder")
        return PreviewBundle(
            validation=validation,
            summary=summary,
            driver_py=placeholder,
            pyproject_toml=placeholder,
            readme=placeholder,
            commands=None,
            project_dir=_draft_project_dir(context, draft),
        )

    spec = validation.spec
    commands = next_step_commands(context, spec)
    return PreviewBundle(
        validation=validation,
        summary=_render_valid_summary(context, language, spec, commands),
        driver_py=generate_driver_py(spec),
        pyproject_toml=generate_pyproject_toml(spec),
        readme=generate_readme(spec, commands, language),
        commands=commands,
        project_dir=str(resolve_scaffold_paths(context, spec).project_dir),
    )


def _render_valid_summary(
    context: ProjectContext,
    language: Language,
    spec: DriverSpec,
    commands: NextStepCommands,
) -> str:
    paths = resolve_scaffold_paths(context, spec)
    lines = [
        t(language, "summary_title_text"),
        "=" * len(t(language, "summary_title_text")),
        "",
        f"{t(language, 'summary_parent_directory')}: {context.working_dir}",
        f"{t(language, 'summary_project_directory')}: {paths.project_dir}",
        f"{t(language, 'summary_plugin_package')}: {spec.plugin_name}",
        f"{t(language, 'summary_project_name')}: {spec.project_name}",
        f"{t(language, 'summary_display_name')}: {spec.display_name}",
        f"{t(language, 'summary_device_id')}: {spec.device_id}",
        f"{t(language, 'summary_providers')}: {spec.providers_display}",
        f"{t(language, 'summary_base_class')}: {spec.driver_base_class}",
        f"{t(language, 'summary_reason')}: {spec.driver_reason}",
        f"{t(language, 'summary_dependencies')}: {', '.join(spec.dependencies)}",
        "",
        f"{t(language, 'summary_streams_title')}:",
    ]
    for index, stream in enumerate(spec.streams, start=1):
        lines.append(
            f"{index}. {stream.display_name} | {stream.modality} | {stream.payload_type} | "
            f"{stream.sample_rate_hz:g} Hz | chunk={stream.chunk_size} | shape={stream.expected_shape}"
        )
    lines.extend(
        [
            "",
            t(language, "commands_title"),
            "-" * len(t(language, "commands_title")),
            f"{t(language, 'success_install')}: {commands.install_plugin_from_parent}",
            f"{t(language, 'success_run_module')}: {commands.run_module}",
            f"{t(language, 'success_run_script')}: {commands.run_script}",
            f"{t(language, 'success_check')}: {commands.test}",
        ]
    )
    return "\n".join(lines)


def _render_invalid_summary(
    context: ProjectContext,
    language: Language,
    draft: ScaffoldDraft,
    validation: DraftValidation,
) -> str:
    display_name = draft.display_name.strip() or to_pascal_case(sanitize_identifier(draft.plugin_name) or draft.plugin_name)
    lines = [
        t(language, "summary_title_text"),
        "=" * len(t(language, "summary_title_text")),
        "",
        f"{t(language, 'summary_parent_directory')}: {context.working_dir}",
        f"{t(language, 'summary_project_directory')}: {_draft_project_dir(context, draft)}",
        f"{t(language, 'summary_plugin_package')}: {sanitize_identifier(draft.plugin_name) or '<invalid>'}",
        f"{t(language, 'summary_display_name')}: {display_name or '<invalid>'}",
        "",
        t(language, "validation_blocked"),
    ]
    for error in validation.field_errors.values():
        lines.append(f"- {error}")
    return "\n".join(lines)


def _draft_project_dir(context: ProjectContext, draft: ScaffoldDraft) -> str:
    plugin_name = sanitize_identifier(draft.plugin_name)
    if not plugin_name:
        return "<invalid>"
    return str(context.working_dir / plugin_name)
