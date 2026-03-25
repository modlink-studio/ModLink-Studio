"""Full-screen Rich TUI for collecting scaffold configuration."""

from __future__ import annotations

import readchar
from readchar import key
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.text import Text

from ..core.context import next_step_commands, resolve_scaffold_paths
from ..core.spec import (
    DriverKind,
    DriverSpec,
    ProjectContext,
    StreamSpec,
    is_valid_device_id,
    make_device_id,
    normalize_device_id,
    normalize_token,
    sanitize_identifier,
    to_pascal_case,
)
from ..i18n import (
    DATA_ARRIVAL_CHOICES,
    PAYLOAD_CHOICES,
    PROVIDER_CHOICES,
    Language,
    choice_description,
    t,
)
from .state import CursorState, StepId, StreamDraft, WizardState, make_default_stream
from .view import ScreenModel, render_buffer, render_group, render_labeled_lines, render_screen

STEP_ORDER: tuple[StepId, ...] = ("identity", "connection", "driver_type", "streams", "dependencies", "summary")
SUMMARY_ACTIONS: tuple[str, ...] = (
    "create",
    "identity",
    "connection",
    "driver_type",
    "streams",
    "dependencies",
)
SHIFT_TAB_KEYS = {"\x00\x0f", "\xe0\x0f"}
ARROW_NEXT = {key.DOWN, key.RIGHT}
ARROW_PREV = {key.UP, key.LEFT}


def prompt_for_driver_spec(
    console: Console,
    context: ProjectContext,
    language: Language = "en",
) -> DriverSpec:
    state = WizardState(context=context, language=language)
    _ensure_stream_count(state)
    _sync_identity_defaults(state)
    _refresh_buffer(state)

    with Live(console=console, screen=True, auto_refresh=False, transient=False) as live:
        while state.finished_spec is None:
            live.update(_render_state(state), refresh=True)
            pressed = readchar.readkey()
            if pressed == key.CTRL_C:
                raise KeyboardInterrupt
            _handle_key(state, pressed)

    return state.finished_spec


def _handle_key(state: WizardState, pressed: str) -> None:
    if state.cursor.step == "summary":
        _handle_summary_key(state, pressed)
        return

    if pressed == key.CTRL_Z:
        _undo(state)
        return
    if pressed in SHIFT_TAB_KEYS:
        _move_to_previous_page(state)
        return
    if pressed == key.TAB:
        _commit_and_advance_page(state)
        return
    if pressed in ("r", "R"):
        _restart_page(state)
        return

    field_id = _current_field_id(state)
    if _field_kind(field_id) == "choice":
        _handle_choice_key(state, pressed, field_id)
        return
    _handle_text_key(state, pressed)


def _handle_summary_key(state: WizardState, pressed: str) -> None:
    if pressed == key.CTRL_Z or pressed in SHIFT_TAB_KEYS:
        _move_to_previous_page(state)
        return
    if pressed in ARROW_NEXT:
        state.cursor = CursorState(
            step="summary",
            field_index=0,
            summary_index=min(state.cursor.summary_index + 1, len(SUMMARY_ACTIONS) - 1),
        )
        return
    if pressed in ARROW_PREV:
        state.cursor = CursorState(
            step="summary",
            field_index=0,
            summary_index=max(state.cursor.summary_index - 1, 0),
        )
        return
    if pressed == key.ENTER:
        selected = SUMMARY_ACTIONS[state.cursor.summary_index]
        if selected == "create":
            state.finished_spec = _build_spec(state)
            return
        state.cursor = CursorState(step=selected, field_index=0, summary_index=0)
        state.error = ""
        _refresh_buffer(state)


def _handle_choice_key(state: WizardState, pressed: str, field_id: str) -> None:
    options = _field_options(state, field_id)
    option_keys = [item[0] for item in options]
    current = state.buffer or _field_display_value(state, field_id)
    try:
        index = option_keys.index(current)
    except ValueError:
        index = 0

    if pressed in ARROW_NEXT:
        state.buffer = option_keys[(index + 1) % len(option_keys)]
        state.buffer_cursor = len(state.buffer)
        state.error = ""
        return
    if pressed in ARROW_PREV:
        state.buffer = option_keys[(index - 1) % len(option_keys)]
        state.buffer_cursor = len(state.buffer)
        state.error = ""
        return
    if len(pressed) == 1 and pressed.isprintable():
        lowered = pressed.lower()
        for option in option_keys:
            if option.startswith(lowered):
                state.buffer = option
                state.buffer_cursor = len(state.buffer)
                state.error = ""
                return
    if pressed == key.ENTER:
        _commit_and_advance_field(state)


def _handle_text_key(state: WizardState, pressed: str) -> None:
    if pressed == key.ENTER:
        _commit_and_advance_field(state)
        return
    if pressed == key.BACKSPACE:
        if state.buffer_cursor > 0:
            state.buffer = state.buffer[: state.buffer_cursor - 1] + state.buffer[state.buffer_cursor :]
            state.buffer_cursor -= 1
        state.error = ""
        return
    if pressed == key.DELETE:
        if state.buffer_cursor < len(state.buffer):
            state.buffer = state.buffer[: state.buffer_cursor] + state.buffer[state.buffer_cursor + 1 :]
        state.error = ""
        return
    if pressed == key.HOME:
        state.buffer_cursor = 0
        return
    if pressed == key.END:
        state.buffer_cursor = len(state.buffer)
        return
    if pressed == key.LEFT:
        state.buffer_cursor = max(0, state.buffer_cursor - 1)
        return
    if pressed == key.RIGHT:
        state.buffer_cursor = min(len(state.buffer), state.buffer_cursor + 1)
        return
    if len(pressed) == 1 and pressed.isprintable():
        state.buffer = state.buffer[: state.buffer_cursor] + pressed + state.buffer[state.buffer_cursor :]
        state.buffer_cursor += 1
        state.error = ""


def _commit_and_advance_field(state: WizardState) -> None:
    if not _commit_current_field(state):
        return
    fields = _fields_for_step(state)
    if state.cursor.field_index + 1 < len(fields):
        state.cursor = CursorState(step=state.cursor.step, field_index=state.cursor.field_index + 1, summary_index=0)
        _refresh_buffer(state)
        return
    _move_to_next_page(state)


def _commit_and_advance_page(state: WizardState) -> None:
    if not _commit_current_field(state):
        return
    _move_to_next_page(state)


def _move_to_next_page(state: WizardState) -> None:
    current_index = STEP_ORDER.index(state.cursor.step)
    next_step = STEP_ORDER[min(current_index + 1, len(STEP_ORDER) - 1)]
    state.cursor = CursorState(step=next_step, field_index=0, summary_index=0)
    state.error = ""
    _refresh_buffer(state)


def _move_to_previous_page(state: WizardState) -> None:
    current_index = STEP_ORDER.index(state.cursor.step)
    if current_index == 0:
        state.cursor = CursorState(step="identity", field_index=0, summary_index=0)
        state.error = ""
        _refresh_buffer(state)
        return
    previous_step = STEP_ORDER[max(0, current_index - 1)]
    previous_fields = _fields_for_step_for_cursor(previous_step, state)
    previous_index = max(0, len(previous_fields) - 1)
    state.cursor = CursorState(step=previous_step, field_index=previous_index, summary_index=0)
    state.error = ""
    _refresh_buffer(state)


def _restart_page(state: WizardState) -> None:
    if state.cursor.step == "summary":
        state.cursor = CursorState(step="summary", field_index=0, summary_index=0)
        state.error = ""
        return

    current_step = state.cursor.step
    restored = None
    while state.history and state.history[-1].cursor.step == current_step:
        restored = state.history.pop()

    if restored is not None:
        state.draft = restored.draft

    _ensure_stream_count(state)
    _sync_identity_defaults(state)
    state.cursor = CursorState(step=current_step, field_index=0, summary_index=0)
    state.error = ""
    _refresh_buffer(state)


def _undo(state: WizardState) -> None:
    if not state.pop_history():
        state.error = ""
        return
    _ensure_stream_count(state)
    _sync_identity_defaults(state)
    state.error = ""
    _refresh_buffer(state)


def _refresh_buffer(state: WizardState) -> None:
    if state.cursor.step == "summary":
        state.buffer = ""
        state.buffer_cursor = 0
        return
    value = _field_display_value(state, _current_field_id(state))
    state.buffer = value
    state.buffer_cursor = len(value)


def _commit_current_field(state: WizardState) -> bool:
    success, error = _apply_field(state, _current_field_id(state), state.buffer)
    if not success:
        state.error = error
        return False
    state.error = ""
    return True


def _apply_field(state: WizardState, field_id: str, raw_value: str) -> tuple[bool, str]:
    language = state.language
    value = raw_value.strip()
    draft = state.draft

    if field_id == "plugin_name":
        normalized = sanitize_identifier(value)
        if not normalized:
            return False, t(language, "plugin_name_error")
        old_default_display = to_pascal_case(draft.plugin_name)
        old_default_device = make_device_id(draft.plugin_name)
        state.push_history()
        draft.plugin_name = normalized
        if not draft.display_name or draft.display_name == old_default_display:
            draft.display_name = to_pascal_case(normalized)
        if not draft.device_id or normalize_device_id(draft.device_id) == old_default_device:
            draft.device_id = make_device_id(normalized)
        _sync_identity_defaults(state)
        return True, ""

    if field_id == "display_name":
        state.push_history()
        draft.display_name = value
        return True, ""

    if field_id == "device_id":
        normalized = normalize_device_id(value or make_device_id(draft.plugin_name))
        if not is_valid_device_id(normalized):
            return False, t(language, "device_id_error")
        state.push_history()
        draft.device_id = normalized
        return True, ""

    if field_id == "providers":
        providers = tuple(
            token
            for token in (normalize_token(item) for item in value.split(","))
            if token
        )
        if not providers:
            return False, t(language, "providers_error")
        state.push_history()
        draft.providers = _unique_tuple(providers)
        return True, ""

    if field_id == "data_arrival":
        if value not in {item.key for item in DATA_ARRIVAL_CHOICES}:
            return False, t(language, "choice_error")
        state.push_history()
        draft.data_arrival = value
        recommended_kind, _ = _recommend_driver_kind(language, draft.data_arrival)
        if draft.driver_kind not in {"driver", "loop"}:
            draft.driver_kind = recommended_kind
        draft.driver_reason = _driver_selection_reason(language, draft.data_arrival, draft.driver_kind)
        return True, ""

    if field_id == "driver_kind":
        if value not in {"driver", "loop"}:
            return False, t(language, "choice_error")
        state.push_history()
        draft.driver_kind = value
        draft.driver_reason = _driver_selection_reason(language, draft.data_arrival, draft.driver_kind)
        return True, ""

    if field_id == "stream_count":
        parsed = _parse_positive_int(value)
        if parsed is None:
            return False, t(language, "positive_int_error")
        state.push_history()
        draft.stream_count = parsed
        _ensure_stream_count(state)
        return True, ""

    if field_id == "dependencies":
        state.push_history()
        draft.dependencies = _unique_tuple(tuple(item.strip() for item in value.split(",") if item.strip()))
        return True, ""

    stream_index, stream_field = _parse_stream_field(field_id)
    stream = draft.streams[stream_index]

    if stream_field == "modality":
        normalized = normalize_token(value)
        if not normalized:
            return False, t(language, "plugin_name_error")
        state.push_history()
        stream.modality = normalized
        return True, ""

    if stream_field == "display_name":
        state.push_history()
        stream.display_name = value
        return True, ""

    if stream_field == "payload_type":
        if value not in {item.key for item in PAYLOAD_CHOICES}:
            return False, t(language, "choice_error")
        state.push_history()
        _apply_payload_defaults(stream, value)
        return True, ""

    if stream_field == "sample_rate_hz":
        parsed_float = _parse_positive_float(value)
        if parsed_float is None:
            return False, t(language, "positive_float_error")
        state.push_history()
        stream.sample_rate_hz = parsed_float
        return True, ""

    if stream_field == "chunk_size":
        parsed = _parse_positive_int(value)
        if parsed is None:
            return False, t(language, "positive_int_error")
        state.push_history()
        stream.chunk_size = parsed
        return True, ""

    if stream_field == "channel_count":
        parsed = _parse_positive_int(value)
        if parsed is None:
            return False, t(language, "positive_int_error")
        state.push_history()
        stream.channel_count = parsed
        stream.channel_names = tuple(f"ch{index + 1}" for index in range(parsed))
        return True, ""

    if stream_field == "channel_names":
        channel_names = tuple(item.strip() for item in value.split(",") if item.strip())
        if not channel_names:
            return False, t(language, "channel_names_error")
        if stream.payload_type == "signal" and len(channel_names) != stream.channel_count:
            return False, t(language, "signal_channel_names_count_error")
        state.push_history()
        stream.channel_names = channel_names
        if stream.payload_type == "signal":
            stream.channel_count = len(channel_names)
        return True, ""

    if stream_field == "unit":
        state.push_history()
        stream.unit = value
        return True, ""

    if stream_field in {"raster_length", "field_height", "field_width", "video_height", "video_width"}:
        parsed = _parse_positive_int(value)
        if parsed is None:
            return False, t(language, "positive_int_error")
        state.push_history()
        setattr(stream, stream_field, parsed)
        return True, ""

    return False, t(language, "choice_error")


def _render_state(state: WizardState):
    language = state.language
    step_title = t(language, f"step_{state.cursor.step}")
    subtitle = t(language, "step_indicator", index=STEP_ORDER.index(state.cursor.step) + 1, total=len(STEP_ORDER))

    if state.cursor.step == "summary":
        current_input = _render_summary_input(state)
        page_summary = _render_summary_driver_table(state)
        draft_summary = _render_summary_streams_table(state)
        status = _render_status_panel(state, summary=True)
        footer = t(language, "navigation_summary")
    else:
        field_id = _current_field_id(state)
        current_input = _render_current_input(state, field_id)
        page_summary = render_labeled_lines(_page_lines(state), highlight_index=state.cursor.field_index)
        draft_summary = render_labeled_lines(_draft_lines(state))
        status = _render_status_panel(state, summary=False)
        footer = t(language, "navigation_editing")

    model = ScreenModel(
        title=t(language, "wizard_title"),
        subtitle=f"{step_title} | {subtitle}",
        current_title=t(language, "current_input_title"),
        page_title=t(language, "current_page_title"),
        draft_title=t(language, "draft_summary_title"),
        status_title=t(language, "status_title"),
        current_input=current_input,
        page_summary=page_summary,
        draft_summary=draft_summary,
        status=status,
        footer=footer,
    )
    return render_screen(model)


def _render_current_input(state: WizardState, field_id: str):
    language = state.language
    label = _field_label(state, field_id)
    help_text = _field_help(state, field_id)
    if _field_kind(field_id) == "text":
        current_value = render_buffer(state.buffer, state.buffer_cursor)
    else:
        current_value = Text(state.buffer, style="bold cyan")

    parts: list[object] = [
        Text(f"{t(language, 'current_field')}: {label}", style="bold green"),
        current_value,
        Text(help_text, style="dim"),
    ]

    examples = _field_examples(state, field_id)
    if examples:
        parts.append(Text(f"{t(language, 'examples')}: {examples}", style="cyan"))

    options = _field_options(state, field_id)
    if options:
        parts.append(Text(t(language, "options_title"), style="bold"))
        for option_key, description in options:
            selected = option_key == state.buffer
            prefix = ">" if selected else " "
            style = "bold yellow" if selected else "white"
            parts.append(Text(f"{prefix} {option_key} - {description}", style=style))

    return render_group(*parts)


def _render_summary_input(state: WizardState):
    language = state.language
    parts: list[object] = [Text(t(language, "summary_help"), style="dim")]
    for index, action in enumerate(SUMMARY_ACTIONS):
        label = _summary_action_label(language, action)
        style = "bold yellow" if index == state.cursor.summary_index else "white"
        prefix = ">" if index == state.cursor.summary_index else " "
        parts.append(Text(f"{prefix} {label}", style=style))
    return render_group(*parts)


def _render_summary_driver_table(state: WizardState) -> Table:
    spec = _build_spec(state)
    language = state.language
    return render_labeled_lines(
        [
            (t(language, "summary_parent_directory"), str(state.context.working_dir)),
            (t(language, "summary_project_directory"), str(resolve_scaffold_paths(state.context, spec).project_dir)),
            (t(language, "summary_plugin_package"), spec.plugin_name),
            (t(language, "summary_project_name"), spec.project_name),
            (t(language, "summary_display_name"), spec.display_name),
            (t(language, "summary_device_id"), spec.device_id),
            (t(language, "summary_providers"), spec.providers_display),
            (t(language, "summary_base_class"), spec.driver_base_class),
            (t(language, "summary_reason"), spec.driver_reason),
            (t(language, "summary_dependencies"), ", ".join(spec.dependencies)),
        ]
    )


def _render_summary_streams_table(state: WizardState) -> Table:
    spec = _build_spec(state)
    language = state.language
    table = Table(title=t(language, "summary_streams_title"), expand=True)
    table.add_column(t(language, "summary_col_display"))
    table.add_column(t(language, "summary_col_modality"))
    table.add_column(t(language, "summary_col_payload"))
    table.add_column(t(language, "summary_col_rate"))
    table.add_column(t(language, "summary_col_chunk"))
    table.add_column(t(language, "summary_col_shape"))
    for stream in spec.streams:
        table.add_row(
            stream.display_name,
            stream.modality,
            stream.payload_type,
            f"{stream.sample_rate_hz:g}",
            str(stream.chunk_size),
            stream.expected_shape,
        )
    return table


def _render_status_panel(state: WizardState, *, summary: bool):
    language = state.language
    lines: list[object] = []
    if state.error:
        lines.append(Text(state.error, style="bold red"))
    else:
        lines.append(Text(t(language, "no_errors"), style="green"))

    if summary:
        commands = next_step_commands(state.context, _build_spec(state))
        lines.extend(
            [
                Text(""),
                Text(f"{t(language, 'success_install')}: {commands.install_plugin_from_parent}", style="dim"),
                Text(f"{t(language, 'success_run_module')}: {commands.run_module}", style="dim"),
                Text(f"{t(language, 'success_run_script')}: {commands.run_script}", style="dim"),
            ]
        )
        return render_group(*lines)

    lines.append(Text(""))
    lines.extend(Text(message, style="dim") for message in _step_status_messages(state))

    if state.cursor.step == "driver_type":
        recommended_kind, reason = _recommend_driver_kind(language, state.draft.data_arrival)
        lines.extend(
            [
                Text(""),
                Text(f"{t(language, 'recommended_base')}: {_base_class_name(language, recommended_kind)}", style="cyan"),
                Text(reason, style="dim"),
            ]
        )

    return render_group(*lines)


def _page_lines(state: WizardState) -> list[tuple[str, str]]:
    return [(_field_label(state, field_id), _field_display_value(state, field_id)) for field_id in _fields_for_step(state)]


def _draft_lines(state: WizardState) -> list[tuple[str, str]]:
    language = state.language
    return [
        (t(language, "summary_plugin_package"), sanitize_identifier(state.draft.plugin_name) or state.draft.plugin_name),
        (t(language, "summary_display_name"), state.draft.display_name or to_pascal_case(state.draft.plugin_name)),
        (t(language, "summary_device_id"), state.draft.device_id or make_device_id(state.draft.plugin_name)),
        (t(language, "summary_providers"), ", ".join(state.draft.providers)),
        (t(language, "summary_base_class"), _base_class_name(language, state.draft.driver_kind)),
        (t(language, "step_streams"), str(state.draft.stream_count)),
        (t(language, "summary_dependencies"), ", ".join(state.draft.dependencies) or "-"),
    ]


def _fields_for_step(state: WizardState) -> list[str]:
    return _fields_for_step_for_cursor(state.cursor.step, state)


def _fields_for_step_for_cursor(step: StepId, state: WizardState) -> list[str]:
    if step == "identity":
        return ["plugin_name", "display_name", "device_id"]
    if step == "connection":
        return ["providers"]
    if step == "driver_type":
        return ["data_arrival", "driver_kind"]
    if step == "dependencies":
        return ["dependencies"]
    if step == "summary":
        return []

    fields = ["stream_count"]
    for index in range(state.draft.stream_count):
        fields.extend(
            [
                f"stream.{index}.modality",
                f"stream.{index}.display_name",
                f"stream.{index}.payload_type",
                f"stream.{index}.sample_rate_hz",
                f"stream.{index}.chunk_size",
            ]
        )
        payload_type = state.draft.streams[index].payload_type
        if payload_type == "signal":
            fields.extend([f"stream.{index}.channel_count", f"stream.{index}.channel_names", f"stream.{index}.unit"])
        elif payload_type == "raster":
            fields.extend([f"stream.{index}.raster_length", f"stream.{index}.channel_names", f"stream.{index}.unit"])
        elif payload_type == "field":
            fields.extend(
                [
                    f"stream.{index}.field_height",
                    f"stream.{index}.field_width",
                    f"stream.{index}.channel_names",
                    f"stream.{index}.unit",
                ]
            )
        else:
            fields.extend([f"stream.{index}.video_height", f"stream.{index}.video_width", f"stream.{index}.channel_names"])
    return fields


def _current_field_id(state: WizardState) -> str:
    fields = _fields_for_step(state)
    index = max(0, min(state.cursor.field_index, len(fields) - 1))
    if index != state.cursor.field_index:
        state.cursor = CursorState(step=state.cursor.step, field_index=index, summary_index=state.cursor.summary_index)
    return fields[index]


def _field_kind(field_id: str) -> str:
    if field_id in {"data_arrival", "driver_kind"} or field_id.endswith(".payload_type"):
        return "choice"
    return "text"


def _field_label(state: WizardState, field_id: str) -> str:
    language = state.language
    label_map = {
        "plugin_name": "plugin_name_label",
        "display_name": "display_name_label",
        "device_id": "device_id_label",
        "providers": "providers_label",
        "data_arrival": "data_arrival_label",
        "driver_kind": "base_class_label",
        "stream_count": "stream_count_label",
        "dependencies": "extra_dependencies_label",
        "modality": "modality_label",
        "display_name_stream": "stream_display_name_label",
        "payload_type": "payload_type_label",
        "sample_rate_hz": "sample_rate_label",
        "chunk_size": "chunk_size_label",
        "channel_count": "channel_count_label",
        "channel_names": "channel_names_label",
        "unit": "unit_label",
        "raster_length": "raster_length_label",
        "field_height": "field_height_label",
        "field_width": "field_width_label",
        "video_height": "frame_height_label",
        "video_width": "frame_width_label",
    }
    if not field_id.startswith("stream."):
        return t(language, label_map[field_id])
    stream_index, stream_field = _parse_stream_field(field_id)
    if stream_field == "display_name":
        return t(language, label_map["display_name_stream"])
    if stream_field == "channel_names":
        payload_type = state.draft.streams[stream_index].payload_type
        if payload_type in {"raster", "field"}:
            return t(language, "channel_semantics_label")
        if payload_type == "video":
            return t(language, "color_channels_label")
    return t(language, label_map[stream_field])


def _field_help(state: WizardState, field_id: str) -> str:
    language = state.language
    if field_id == "plugin_name":
        return t(language, "plugin_name_help")
    if field_id == "display_name":
        return t(language, "display_name_help")
    if field_id == "device_id":
        return t(language, "device_id_help")
    if field_id == "providers":
        return f"{t(language, 'connection_hint')} {t(language, 'connection_hint_extra')} {t(language, 'providers_help')}"
    if field_id == "data_arrival":
        return f"{t(language, 'driver_type_hint_1')} {t(language, 'driver_type_hint_2')}"
    if field_id == "driver_kind":
        return t(language, "base_class_help")
    if field_id == "stream_count":
        return f"{t(language, 'streams_hint_1')} {t(language, 'streams_hint_2')} {t(language, 'streams_hint_3')}"
    if field_id == "dependencies":
        return t(language, "dependencies_hint")

    stream_index, stream_field = _parse_stream_field(field_id)
    help_map = {
        "modality": "modality_help",
        "display_name": "stream_display_name_help",
        "payload_type": "payload_type_help",
        "sample_rate_hz": "sample_rate_help",
        "chunk_size": "chunk_size_help",
        "channel_count": "channel_count_help",
        "channel_names": "channel_names_help",
        "unit": "unit_help",
        "raster_length": "raster_length_help",
        "field_height": "field_height_help",
        "field_width": "field_width_help",
        "video_height": "frame_height_help",
        "video_width": "frame_width_help",
    }
    if stream_field == "payload_type":
        return f"{t(language, 'payload_hint_1')} {t(language, 'payload_hint_2')} {t(language, 'payload_hint_3')}"
    if stream_field == "channel_names":
        payload_type = state.draft.streams[stream_index].payload_type
        if payload_type == "video":
            return t(language, "color_channels_help")
        if payload_type in {"raster", "field"}:
            return t(language, "channel_semantics_help")
    return t(language, help_map[stream_field])


def _field_examples(state: WizardState, field_id: str) -> str:
    language = state.language
    if field_id == "providers":
        return t(language, "connection_examples")
    if field_id == "dependencies":
        return t(language, "dependencies_examples")
    return ""


def _field_options(state: WizardState, field_id: str) -> list[tuple[str, str]]:
    language = state.language
    if field_id == "providers":
        return [(item.key, choice_description(item, language)) for item in PROVIDER_CHOICES]
    if field_id == "data_arrival":
        return [(item.key, choice_description(item, language)) for item in DATA_ARRIVAL_CHOICES]
    if field_id == "driver_kind":
        return [
            ("driver", t(language, "base_driver_option")),
            ("loop", t(language, "base_loop_option")),
        ]
    if field_id.endswith(".payload_type"):
        return [(item.key, choice_description(item, language)) for item in PAYLOAD_CHOICES]
    return []


def _field_display_value(state: WizardState, field_id: str) -> str:
    draft = state.draft
    if field_id == "plugin_name":
        return draft.plugin_name
    if field_id == "display_name":
        return draft.display_name or to_pascal_case(draft.plugin_name)
    if field_id == "device_id":
        return draft.device_id or make_device_id(draft.plugin_name)
    if field_id == "providers":
        return ", ".join(draft.providers)
    if field_id == "data_arrival":
        return draft.data_arrival
    if field_id == "driver_kind":
        return draft.driver_kind
    if field_id == "stream_count":
        return str(draft.stream_count)
    if field_id == "dependencies":
        return ", ".join(draft.dependencies)

    stream_index, stream_field = _parse_stream_field(field_id)
    stream = draft.streams[stream_index]
    if stream_field in {"modality", "display_name", "payload_type", "unit"}:
        return str(getattr(stream, stream_field))
    if stream_field == "channel_names":
        return ", ".join(stream.channel_names)
    if stream_field == "sample_rate_hz":
        return f"{stream.sample_rate_hz:g}"
    return str(getattr(stream, stream_field))


def _parse_stream_field(field_id: str) -> tuple[int, str]:
    _, stream_index, stream_field = field_id.split(".", 2)
    return int(stream_index), stream_field


def _ensure_stream_count(state: WizardState) -> None:
    while len(state.draft.streams) < state.draft.stream_count:
        state.draft.streams.append(make_default_stream(len(state.draft.streams)))
    if len(state.draft.streams) > state.draft.stream_count:
        state.draft.streams = state.draft.streams[: state.draft.stream_count]


def _apply_payload_defaults(stream: StreamDraft, payload_type: str) -> None:
    stream.payload_type = payload_type
    if payload_type == "signal":
        stream.sample_rate_hz = 250.0
        stream.chunk_size = 25
        stream.channel_count = 2
        stream.channel_names = ("ch1", "ch2")
        stream.unit = stream.unit or ""
    elif payload_type == "raster":
        stream.sample_rate_hz = 10.0
        stream.chunk_size = 1
        stream.channel_count = 1
        stream.channel_names = ("intensity",)
        stream.raster_length = 128
        stream.unit = stream.unit or ""
    elif payload_type == "field":
        stream.sample_rate_hz = 10.0
        stream.chunk_size = 1
        stream.channel_count = 1
        stream.channel_names = ("intensity",)
        stream.field_height = 48
        stream.field_width = 48
        stream.unit = stream.unit or ""
    else:
        stream.sample_rate_hz = 30.0
        stream.chunk_size = 1
        stream.channel_count = 3
        stream.channel_names = ("red", "green", "blue")
        stream.video_height = 480
        stream.video_width = 640
        stream.unit = ""


def _parse_positive_int(value: str) -> int | None:
    try:
        parsed = int(value)
    except ValueError:
        return None
    return parsed if parsed > 0 else None


def _parse_positive_float(value: str) -> float | None:
    try:
        parsed = float(value)
    except ValueError:
        return None
    return parsed if parsed > 0 else None


def _sync_identity_defaults(state: WizardState) -> None:
    if not state.draft.driver_reason:
        state.draft.driver_reason = _driver_selection_reason(
            state.language,
            state.draft.data_arrival,
            state.draft.driver_kind,
        )


def _build_spec(state: WizardState) -> DriverSpec:
    draft = state.draft
    streams = tuple(
        StreamSpec(
            modality=stream.modality,
            payload_type=stream.payload_type,
            display_name=stream.display_name,
            sample_rate_hz=stream.sample_rate_hz,
            chunk_size=stream.chunk_size,
            channel_names=stream.channel_names,
            unit=stream.unit.strip() or None,
            raster_length=stream.raster_length if stream.payload_type == "raster" else None,
            field_height=stream.field_height if stream.payload_type == "field" else None,
            field_width=stream.field_width if stream.payload_type == "field" else None,
            video_height=stream.video_height if stream.payload_type == "video" else None,
            video_width=stream.video_width if stream.payload_type == "video" else None,
        )
        for stream in draft.streams[: draft.stream_count]
    )
    return DriverSpec(
        plugin_name=draft.plugin_name,
        display_name=draft.display_name or to_pascal_case(draft.plugin_name),
        device_id=draft.device_id or make_device_id(draft.plugin_name),
        providers=_unique_tuple(draft.providers),
        driver_kind=draft.driver_kind,
        driver_reason=_driver_selection_reason(state.language, draft.data_arrival, draft.driver_kind),
        data_arrival=draft.data_arrival,
        streams=streams,
        dependencies=draft.dependencies,
    )


def _recommend_driver_kind(language: Language, data_arrival: str) -> tuple[DriverKind, str]:
    if data_arrival == "poll":
        return "loop", t(language, "reason_poll_loop")
    if data_arrival == "push":
        return "driver", t(language, "reason_push_driver")
    return "driver", t(language, "reason_unsure_driver")


def _driver_selection_reason(language: Language, data_arrival: str, driver_kind: str) -> str:
    if data_arrival == "push":
        return t(language, "reason_push_driver") if driver_kind == "driver" else t(language, "reason_push_loop")
    if data_arrival == "poll":
        return t(language, "reason_poll_loop") if driver_kind == "loop" else t(language, "reason_poll_driver")
    return t(language, "reason_unsure_driver") if driver_kind == "driver" else t(language, "reason_unsure_loop")


def _summary_action_label(language: Language, action: str) -> str:
    label_map = {
        "create": "summary_create",
        "identity": "summary_edit_identity",
        "connection": "summary_edit_connection",
        "driver_type": "summary_edit_driver_type",
        "streams": "summary_edit_streams",
        "dependencies": "summary_edit_dependencies",
    }
    return t(language, label_map[action])


def _base_class_name(language: Language, driver_kind: DriverKind | str) -> str:
    return t(language, "base_loop_name") if driver_kind == "loop" else t(language, "base_driver_name")


def _step_status_messages(state: WizardState) -> tuple[str, ...]:
    language = state.language
    if state.cursor.step == "identity":
        return (
            t(language, "identity_hint"),
            f"{t(language, 'current_directory')}: {state.context.working_dir}",
            t(language, "layout_body"),
        )
    if state.cursor.step == "connection":
        return (
            t(language, "connection_hint"),
            t(language, "connection_hint_extra"),
        )
    if state.cursor.step == "driver_type":
        return (t(language, "driver_type_hint_3"),)
    if state.cursor.step == "streams":
        return (
            t(language, "stream_panel_hint"),
            t(language, "streams_hint_4"),
        )
    return (t(language, "dependencies_hint"),)


def _unique_tuple(values: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not value or value in seen:
            continue
        result.append(value)
        seen.add(value)
    return tuple(result)
