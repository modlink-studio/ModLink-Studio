"""Interactive prompts for scaffold configuration."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from .i18n import DATA_ARRIVAL_ORDER, DRIVER_KIND_ORDER, PAYLOAD_TYPE_ORDER, get_copy
from .models import create_default_draft, create_default_stream, Draft, Language, PayloadType, StreamDraft
from .validation import (
    apply_data_arrival_defaults,
    apply_payload_defaults,
    apply_plugin_name_defaults,
    recommended_driver_kind,
    sanitize_identifier,
    to_pascal_case,
    make_device_id,
)


console = Console()


def prompt_identity(draft: Draft, language: Language) -> Draft:
    """Prompt for identity configuration."""
    copy = get_copy(language)

    console.print(Panel(copy.get("identity_section", "Identity"), style="bold cyan"))

    # Plugin name
    plugin_name = Prompt.ask(
        copy.get("plugin_name_prompt", "Enter plugin name"),
        default=draft.plugin_name,
    )
    draft = apply_plugin_name_defaults(draft, plugin_name)

    # Display name
    display_name_default = to_pascal_case(sanitize_identifier(plugin_name)) if sanitize_identifier(plugin_name) else ""
    display_name = Prompt.ask(
        copy.get("display_name_prompt", "Enter display name"),
        default=draft.display_name or display_name_default,
    )
    draft = Draft(
        plugin_name=draft.plugin_name,
        display_name=display_name,
        device_id=draft.device_id,
        providers_text=draft.providers_text,
        data_arrival=draft.data_arrival,
        driver_kind=draft.driver_kind,
        dependencies_text=draft.dependencies_text,
        streams=draft.streams,
    )

    # Device ID
    device_id_default = draft.device_id or make_device_id(plugin_name)
    device_id = Prompt.ask(
        copy.get("device_id_prompt", "Enter device ID"),
        default=device_id_default,
    )
    draft = Draft(
        plugin_name=draft.plugin_name,
        display_name=draft.display_name,
        device_id=device_id,
        providers_text=draft.providers_text,
        data_arrival=draft.data_arrival,
        driver_kind=draft.driver_kind,
        dependencies_text=draft.dependencies_text,
        streams=draft.streams,
    )

    return draft


def prompt_connection(draft: Draft, language: Language) -> Draft:
    """Prompt for connection configuration."""
    copy = get_copy(language)

    console.print(Panel(copy.get("connection_section", "Connection"), style="bold cyan"))

    # Providers
    providers = Prompt.ask(
        copy.get("providers_prompt", "Enter providers"),
        default=draft.providers_text,
    )

    # Data arrival
    console.print(f"\n{copy.get('data_arrival_prompt', 'Select data arrival mode')}:")
    arrival_descriptions = {
        "push": copy.get("push_description", "Device pushes data"),
        "poll": copy.get("poll_description", "Host polls device"),
        "unsure": copy.get("unsure_description", "Not sure yet"),
    }
    for i, mode in enumerate(DATA_ARRIVAL_ORDER, 1):
        desc = arrival_descriptions.get(mode, mode)
        console.print(f"  {i}. {mode} - {desc}")

    arrival_choice = Prompt.ask(
        "Choice",
        default=str(DATA_ARRIVAL_ORDER.index(draft.data_arrival) + 1),
    )
    try:
        arrival_index = int(arrival_choice) - 1
        data_arrival = DATA_ARRIVAL_ORDER[arrival_index] if 0 <= arrival_index < len(DATA_ARRIVAL_ORDER) else draft.data_arrival
    except ValueError:
        data_arrival = draft.data_arrival

    draft = apply_data_arrival_defaults(draft, data_arrival)

    return Draft(
        plugin_name=draft.plugin_name,
        display_name=draft.display_name,
        device_id=draft.device_id,
        providers_text=providers,
        data_arrival=draft.data_arrival,
        driver_kind=draft.driver_kind,
        dependencies_text=draft.dependencies_text,
        streams=draft.streams,
    )


def prompt_driver(draft: Draft, language: Language) -> Draft:
    """Prompt for driver configuration."""
    copy = get_copy(language)

    console.print(Panel(copy.get("driver_section", "Driver"), style="bold cyan"))

    recommended = recommended_driver_kind(draft.data_arrival)

    # Driver kind
    console.print(f"\n{copy.get('driver_kind_prompt', 'Select driver kind')}:")
    driver_descriptions = {
        "driver": copy.get("driver_description", "Callback-based"),
        "loop": copy.get("loop_description", "Poll-based"),
    }
    for i, kind in enumerate(DRIVER_KIND_ORDER, 1):
        desc = driver_descriptions.get(kind, kind)
        marker = " (recommended)" if kind == recommended else ""
        console.print(f"  {i}. {kind} - {desc}{marker}")

    driver_choice = Prompt.ask(
        "Choice",
        default=str(DRIVER_KIND_ORDER.index(draft.driver_kind) + 1),
    )
    try:
        driver_index = int(driver_choice) - 1
        driver_kind = DRIVER_KIND_ORDER[driver_index] if 0 <= driver_index < len(DRIVER_KIND_ORDER) else draft.driver_kind
    except ValueError:
        driver_kind = draft.driver_kind

    return Draft(
        plugin_name=draft.plugin_name,
        display_name=draft.display_name,
        device_id=draft.device_id,
        providers_text=draft.providers_text,
        data_arrival=draft.data_arrival,
        driver_kind=driver_kind,
        dependencies_text=draft.dependencies_text,
        streams=draft.streams,
    )


def prompt_stream(stream: StreamDraft, index: int, language: Language) -> StreamDraft:
    """Prompt for stream configuration."""
    copy = get_copy(language)

    console.print(f"\n[bold]{copy.get('add_stream_prompt', 'Configure stream').replace('{index}', str(index + 1))}[/bold]")

    # Stream key
    stream_key = Prompt.ask(
        copy.get("stream_key_prompt", "Stream key"),
        default=stream.stream_key,
    )

    # Display name
    display_name = Prompt.ask(
        copy.get("stream_name_prompt", "Stream display name"),
        default=stream.display_name,
    )

    # Payload type
    console.print(f"\n{copy.get('payload_type_prompt', 'Payload type')}:")
    payload_descriptions = {
        "signal": copy.get("signal_description", "Time-series signal"),
        "raster": copy.get("raster_description", "1D raster scan"),
        "field": copy.get("field_description", "2D field data"),
        "video": copy.get("video_description", "Video frames"),
    }
    for i, ptype in enumerate(PAYLOAD_TYPE_ORDER, 1):
        desc = payload_descriptions.get(ptype, ptype)
        console.print(f"  {i}. {ptype} - {desc}")

    payload_choice = Prompt.ask(
        "Choice",
        default=str(PAYLOAD_TYPE_ORDER.index(stream.payload_type) + 1),
    )
    try:
        payload_index = int(payload_choice) - 1
        payload_type: PayloadType = PAYLOAD_TYPE_ORDER[payload_index] if 0 <= payload_index < len(PAYLOAD_TYPE_ORDER) else stream.payload_type
    except ValueError:
        payload_type = stream.payload_type

    # Apply payload defaults
    stream = apply_payload_defaults(
        StreamDraft(
            stream_key=stream_key,
            display_name=display_name,
            payload_type=payload_type,
            sample_rate_hz=stream.sample_rate_hz,
            chunk_size=stream.chunk_size,
            channel_count=stream.channel_count,
            channel_names=stream.channel_names,
            unit=stream.unit,
            raster_length=stream.raster_length,
            field_height=stream.field_height,
            field_width=stream.field_width,
            video_height=stream.video_height,
            video_width=stream.video_width,
        ),
        payload_type,
    )

    # Common fields
    sample_rate = Prompt.ask(
        copy.get("sample_rate_label", "Sample rate (Hz)"),
        default=stream.sample_rate_hz,
    )
    chunk_size = Prompt.ask(
        copy.get("chunk_size_label", "Chunk size"),
        default=stream.chunk_size,
    )
    channel_names = Prompt.ask(
        copy.get("channel_names_label", "Channel names"),
        default=stream.channel_names,
    )
    unit = Prompt.ask(
        copy.get("unit_label", "Unit"),
        default=stream.unit or "",
    )

    stream = StreamDraft(
        stream_key=stream.stream_key,
        display_name=stream.display_name,
        payload_type=stream.payload_type,
        sample_rate_hz=sample_rate,
        chunk_size=chunk_size,
        channel_count=stream.channel_count,
        channel_names=channel_names,
        unit=unit,
        raster_length=stream.raster_length,
        field_height=stream.field_height,
        field_width=stream.field_width,
        video_height=stream.video_height,
        video_width=stream.video_width,
    )

    # Type-specific fields
    if payload_type == "raster":
        raster_length = Prompt.ask(
            copy.get("raster_length_label", "Raster length"),
            default=stream.raster_length,
        )
        stream = StreamDraft(**{**stream.model_dump(), "raster_length": raster_length})

    if payload_type == "field":
        field_height = Prompt.ask(
            copy.get("field_height_label", "Field height"),
            default=stream.field_height,
        )
        field_width = Prompt.ask(
            copy.get("field_width_label", "Field width"),
            default=stream.field_width,
        )
        stream = StreamDraft(**{**stream.model_dump(), "field_height": field_height, "field_width": field_width})

    if payload_type == "video":
        video_height = Prompt.ask(
            copy.get("video_height_label", "Video height"),
            default=stream.video_height,
        )
        video_width = Prompt.ask(
            copy.get("video_width_label", "Video width"),
            default=stream.video_width,
        )
        stream = StreamDraft(**{**stream.model_dump(), "video_height": video_height, "video_width": video_width})

    return stream


def prompt_streams(draft: Draft, language: Language) -> Draft:
    """Prompt for all streams configuration."""
    copy = get_copy(language)

    console.print(Panel(copy.get("streams_section", "Streams"), style="bold cyan"))

    streams: list[StreamDraft] = []

    # First stream (required)
    first_stream = prompt_stream(draft.streams[0] if draft.streams else create_default_stream(0), 0, language)
    streams.append(first_stream)

    # Additional streams
    index = 1
    while Confirm.ask(copy.get("add_more_streams_prompt", "Add another stream?"), default=False):
        new_stream = prompt_stream(create_default_stream(index), index, language)
        streams.append(new_stream)
        index += 1

    return Draft(
        plugin_name=draft.plugin_name,
        display_name=draft.display_name,
        device_id=draft.device_id,
        providers_text=draft.providers_text,
        data_arrival=draft.data_arrival,
        driver_kind=draft.driver_kind,
        dependencies_text=draft.dependencies_text,
        streams=streams,
    )


def prompt_dependencies(draft: Draft, language: Language) -> Draft:
    """Prompt for dependencies configuration."""
    copy = get_copy(language)

    console.print(Panel(copy.get("dependencies_section", "Dependencies"), style="bold cyan"))

    dependencies = Prompt.ask(
        copy.get("dependencies_prompt", "Enter additional dependencies"),
        default=draft.dependencies_text,
    )

    return Draft(
        plugin_name=draft.plugin_name,
        display_name=draft.display_name,
        device_id=draft.device_id,
        providers_text=draft.providers_text,
        data_arrival=draft.data_arrival,
        driver_kind=draft.driver_kind,
        dependencies_text=dependencies,
        streams=draft.streams,
    )


def show_summary(draft: Draft, language: Language) -> None:
    """Show configuration summary."""
    copy = get_copy(language)

    table = Table(title=copy.get("summary_title", "Driver Summary"))
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="green")

    table.add_row(copy.get("plugin_name_label", "Plugin name"), draft.plugin_name)
    table.add_row(copy.get("display_name_label", "Display name"), draft.display_name)
    table.add_row(copy.get("device_id_label", "Device ID"), draft.device_id)
    table.add_row(copy.get("providers_label", "Providers"), draft.providers_text)
    table.add_row(copy.get("data_arrival_label", "Data arrival"), draft.data_arrival)
    table.add_row(copy.get("driver_kind_label", "Driver kind"), draft.driver_kind)
    table.add_row(copy.get("stream_count_label", "Stream count"), str(len(draft.streams)))
    table.add_row(copy.get("dependencies_label", "Dependencies"), draft.dependencies_text or "none")

    console.print(table)


def prompt_scaffold(language: Language, cwd: str) -> Draft | None:
    """Run full scaffold prompt flow."""
    copy = get_copy(language)

    console.print(Panel(copy.get("app_title", "ModLink Plugin Scaffold"), style="bold magenta"))

    # Start with default draft
    draft = create_default_draft()

    # Prompt each section
    draft = prompt_identity(draft, language)
    draft = prompt_connection(draft, language)
    draft = prompt_driver(draft, language)
    draft = prompt_streams(draft, language)
    draft = prompt_dependencies(draft, language)

    # Show summary
    show_summary(draft, language)

    # Confirm generation
    if not Confirm.ask(copy.get("confirm_generate_prompt", "Generate project?"), default=True):
        console.print("[yellow]Cancelled[/yellow]")
        return None

    return draft


def show_result(project: GeneratedProject, language: Language) -> None:
    """Show generation result."""
    copy = get_copy(language)

    console.print(Panel(copy.get("result_title", "Generated Successfully!"), style="bold green"))

    # Show files
    console.print(f"\n[bold]{copy.get('result_files', 'Files created')}:[/bold]")
    for file in project.written_files:
        console.print(f"  • {file}")

    # Show commands
    console.print(f"\n[bold]{copy.get('result_commands', 'Next steps')}:[/bold]")
    console.print(f"  1. cd {Path(project.project_dir).name}")
    console.print(f"  2. {copy.get('install_command', 'Install: python -m pip install -e .')}")
    console.print(f"  3. {copy.get('test_command', 'Test: python -m pytest')}")
    console.print(f"  4. {copy.get('run_command', 'Run: python -m modlink_studio')}")