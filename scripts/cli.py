#!/usr/bin/env python3
"""ModLink Plugin Scaffold Generator.

Creates a new driver plugin with all necessary files and configuration.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Literal

from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.table import Table

console = Console()


def sanitize_identifier(name: str) -> str:
    """Convert a name to a valid Python identifier."""
    # Replace spaces and hyphens with underscores, remove invalid chars
    name = re.sub(r"[^\w\s-]", "", name)
    name = re.sub(r"[-\s]+", "_", name)
    return name.lower().strip("_")


def to_pascal_case(name: str) -> str:
    """Convert snake_case or kebab-case to PascalCase."""
    parts = re.split(r"[_-]+", name)
    return "".join(word.capitalize() for word in parts if word)


def to_snake_case(name: str) -> str:
    """Convert PascalCase or spaces to snake_case."""
    name = re.sub(r"([A-Z])", r"_\1", name).lower()
    name = re.sub(r"[_\s-]+", "_", name)
    return name.strip("_")


class PluginConfig:
    """Configuration for the new plugin."""

    def __init__(
        self,
        plugin_name: str,
        driver_type: Literal["driver", "loop"],
        device_id: str,
        display_name: str,
        provider: str,
        modality: str,
        payload_type: Literal["line", "plane", "video"],
        sample_rate: float,
        chunk_size: int,
        channel_names: list[str],
        unit: str | None,
        dependencies: list[str],
    ) -> None:
        self.plugin_name = sanitize_identifier(plugin_name).replace("-", "_")
        self.plugin_dir_name = sanitize_identifier(plugin_name).replace("_", "-")
        self.driver_type = driver_type
        self.device_id = device_id
        self.display_name = display_name
        self.provider = provider
        self.modality = modality
        self.payload_type = payload_type
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.channel_names = tuple(channel_names)
        self.unit = unit
        self.dependencies = dependencies

        # Derived names
        self.class_name = to_pascal_case(self.plugin_name)
    @property
    def driver_base_class(self) -> str:
        return "LoopDriver" if self.driver_type == "loop" else "Driver"

    @property
    def providers_tuple(self) -> str:
        return f'("{self.provider}",)'


def prompt_for_config() -> PluginConfig:
    """Interactively prompt user for plugin configuration."""

    # Header
    console.print("\n")
    console.print(
        Panel(
            "[bold cyan]ModLink Plugin Scaffold Generator[/bold cyan]\n\n"
            "This wizard will guide you through creating a new driver plugin.",
            title="[bold]Welcome[/bold]",
            border_style="cyan",
            padding=(1, 2),
        )
    )

    # Basic info
    console.print("\n[bold yellow]Step 1: Basic Information[/bold yellow]\n")

    plugin_name = Prompt.ask(
        "[cyan]Plugin name[/cyan]",
        default="my-device",
        console=console,
    )
    while not plugin_name:
        console.print("[red]Plugin name is required[/red]")
        plugin_name = Prompt.ask("[cyan]Plugin name[/cyan]", console=console)

    display_name = Prompt.ask(
        "[cyan]Display name[/cyan]",
        default=to_pascal_case(plugin_name),
        console=console,
    )

    default_device_id = f"{to_snake_case(plugin_name)}.01"
    device_id = Prompt.ask(
        "[cyan]Device ID[/cyan]",
        default=default_device_id,
        console=console,
    )

    # Driver type
    console.print("\n[bold yellow]Step 2: Driver Type[/bold yellow]\n")

    console.print("[dim]Choose the base class for your driver:[/dim]")
    console.print(
        "  [bold blue]1.[/bold blue] [cyan]Driver[/cyan]      - For callback/async style drivers"
    )
    console.print(
        "  [bold blue]2.[/bold blue] [cyan]LoopDriver[/cyan]  - For polling/timer-based drivers"
    )

    driver_choice = Prompt.ask(
        "\n[cyan]Choose[/cyan]",
        choices=["1", "2"],
        default="2",
        console=console,
    )
    driver_type = "loop" if driver_choice == "2" else "driver"

    # Connection info
    console.print("\n[bold yellow]Step 3: Connection[/bold yellow]\n")

    provider = Prompt.ask(
        "[cyan]Provider name[/cyan]",
        default="serial",
        show_default=True,
        console=console,
    )
    console.print("[dim]Examples: serial, ble, tcp, usb, video[/dim]")

    # Stream configuration
    console.print("\n[bold yellow]Step 4: Stream Configuration[/bold yellow]\n")

    modality = Prompt.ask(
        "[cyan]Modality[/cyan]",
        default="data",
        console=console,
    )
    console.print("[dim]Examples: eeg, video, audio, accel, gyro, temperature[/dim]")

    console.print("\n[dim]Payload type determines how data is displayed:[/dim]")
    console.print("  • [bold cyan]line[/bold cyan]  - Multi-channel time-series data")
    console.print("  • [bold cyan]plane[/cyan] - 2D image/sensor array")
    console.print("  • [bold cyan]video[/cyan] - RGB video stream")

    payload_choice = Prompt.ask(
        "\n[cyan]Payload type[/cyan]",
        choices=["line", "plane", "video"],
        default="line",
        console=console,
    )
    payload_type: Literal["line", "plane", "video"] = payload_choice

    # Sample rate and chunk size
    console.print("\n[bold yellow]Step 5: Data Settings[/bold yellow]\n")

    sample_rate = float(
        Prompt.ask(
            "[cyan]Sample rate (Hz)[/cyan]",
            default="30",
            console=console,
        )
    )

    chunk_size = IntPrompt.ask(
        "[cyan]Chunk size[/cyan]",
        default=1,
        console=console,
    )

    # Channels
    console.print("\n[bold yellow]Step 6: Channels[/bold yellow]\n")

    channels_input = Prompt.ask(
        "[cyan]Channel names[/cyan] [dim](comma-separated)[/dim]",
        default="ch1,ch2",
        console=console,
    )
    channel_names = [c.strip() for c in channels_input.split(",") if c.strip()]

    unit = (
        Prompt.ask(
            "[cyan]Unit[/cyan]",
            default="",
            console=console,
        )
        or None
    )

    # Dependencies
    console.print("\n[bold yellow]Step 7: Dependencies[/bold yellow]\n")
    console.print("[dim]Additional Python packages (comma-separated)[/dim]")
    console.print("[dim]Example: opencv-python>=4.0, bleak>=0.20[/dim]")

    deps_input = Prompt.ask(
        "[cyan]Extra dependencies[/cyan]",
        default="",
        console=console,
    )
    dependencies = []
    if deps_input:
        dependencies = [d.strip() for d in deps_input.split(",")]
    dependencies.extend(["modlink-sdk", "numpy>=2.3.3"])

    # Summary
    console.print("\n[bold yellow]Summary[/bold yellow]\n")

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Plugin name:", plugin_name)
    table.add_row("Display name:", display_name)
    table.add_row("Device ID:", device_id)
    table.add_row("Driver type:", "LoopDriver" if driver_type == "loop" else "Driver")
    table.add_row("Provider:", provider)
    table.add_row("Modality:", modality)
    table.add_row("Payload type:", payload_type)
    table.add_row("Sample rate:", f"{sample_rate} Hz")
    table.add_row("Chunk size:", str(chunk_size))
    table.add_row("Channels:", ", ".join(channel_names))
    table.add_row("Unit:", unit or "[dim]none[/dim]")
    table.add_row("Dependencies:", ", ".join(dependencies))

    console.print(table)

    if not Confirm.ask(
        "\n[cyan]Create plugin with these settings?[/cyan]",
        default=True,
        console=console,
    ):
        console.print("\n[yellow]Cancelled.[/yellow]")
        raise SystemExit(0)

    return PluginConfig(
        plugin_name=plugin_name,
        driver_type=driver_type,
        device_id=device_id,
        display_name=display_name,
        provider=provider,
        modality=modality,
        payload_type=payload_type,
        sample_rate=sample_rate,
        chunk_size=chunk_size,
        channel_names=channel_names,
        unit=unit,
        dependencies=dependencies,
    )


def generate_driver_py(config: PluginConfig) -> str:
    """Generate the driver.py content."""
    channel_names_tuple = str(config.channel_names)

    if config.driver_type == "loop":
        loop_interval = f"int(round(1000 * {config.chunk_size} / {config.sample_rate}))"
        extra_methods = f"""
    loop_interval_ms = {loop_interval}

    def on_loop_started(self) -> None:
        raise NotImplementedError(f"{{type(self).__name__}} must implement on_loop_started")

    def on_loop_stopped(self) -> None:
        raise NotImplementedError(f"{{type(self).__name__}} must implement on_loop_stopped")

    def loop(self) -> None:
        raise NotImplementedError(f"{{type(self).__name__}} must implement loop")
"""
    else:
        extra_methods = """
    def start_streaming(self) -> None:
        raise NotImplementedError(f"{type(self).__name__} must implement start_streaming")

    def stop_streaming(self) -> None:
        raise NotImplementedError(f"{type(self).__name__} must implement stop_streaming")
"""

    unit_line = (
        f'        unit="{config.unit}",' if config.unit else "        unit=None,"
    )

    return f'''"""{config.display_name} driver implementation."""

from __future__ import annotations

import time

import numpy as np

from modlink_sdk import {config.driver_base_class}, FrameEnvelope, SearchResult, StreamDescriptor

DEFAULT_DEVICE_ID = "{config.device_id}"
DEFAULT_SAMPLE_RATE_HZ = {config.sample_rate}
DEFAULT_CHUNK_SIZE = {config.chunk_size}
DEFAULT_CHANNEL_NAMES = {channel_names_tuple}


class {config.class_name}Driver({config.driver_base_class}):
    supported_providers = {config.providers_tuple}

    def __init__(self) -> None:
        super().__init__()
        # Add your instance variables here
        self._seq = 0

    @property
    def device_id(self) -> str:
        return DEFAULT_DEVICE_ID

    @property
    def display_name(self) -> str:
        return "{config.display_name}"

    def descriptors(self) -> list[StreamDescriptor]:
        return [
            StreamDescriptor(
                device_id=self.device_id,
                modality="{config.modality}",
                payload_type="{config.payload_type}",
                nominal_sample_rate_hz=DEFAULT_SAMPLE_RATE_HZ,
                chunk_size=DEFAULT_CHUNK_SIZE,
                channel_names=DEFAULT_CHANNEL_NAMES,
{unit_line}
                display_name="{config.display_name} Stream",
            )
        ]

    def search(self, provider: str) -> list[SearchResult]:
        if provider != "{config.provider}":
            raise ValueError("{config.class_name} search provider must be '{config.provider}'")

        # TODO: Implement device discovery
        # Return a list of SearchResult objects with discovered devices
        return []

    def connect_device(self, config: SearchResult) -> None:
        # TODO: Implement device connection
        # Use config.extra to get connection parameters
        self._seq = 0

    def disconnect_device(self) -> None:
        # TODO: Implement device disconnection
        self.stop_streaming()
        self._seq = 0
{extra_methods}
'''


def generate_factory_py(config: PluginConfig) -> str:
    """Generate the factory.py content."""
    return f'''"""Factory function for {config.class_name} driver."""

from __future__ import annotations

from .driver import {config.class_name}Driver


def create_driver() -> {config.class_name}Driver:
    return {config.class_name}Driver()
'''


def generate_init_py(config: PluginConfig) -> str:
    """Generate the __init__.py content."""
    return f'''"""{{config.display_name}} driver plugin for ModLink Studio."""

from __future__ import annotations

from .driver import {config.class_name}Driver

__all__ = ["{config.class_name}Driver"]
'''


def generate_pyproject_toml(config: PluginConfig) -> str:
    """Generate the pyproject.toml content."""
    deps = "\n".join(f'    "{dep}",' for dep in config.dependencies)
    entry_point = config.plugin_dir_name.replace("-", "")

    return f"""[project]
name = "{config.plugin_dir_name}"
version = "0.1.0"
description = "{config.display_name} driver plugin for ModLink Studio"
readme = "README.md"
requires-python = ">=3.13"
dependencies = [
{deps}
]

[project.entry-points."modlink.drivers"]
{config.plugin_dir_name} = "{entry_point}.factory:create_driver"

[tool.uv.sources]
modlink-sdk = {{ path = "../../packages/modlink_sdk", editable = true }}

[build-system]
requires = ["uv_build>=0.10.9,<0.11.0"]
build-backend = "uv_build"

[tool.uv.build-backend]
module-root = ""
"""


def update_root_pyproject(config: PluginConfig, repo_root: Path) -> None:
    """Update the root pyproject.toml to include the new plugin."""
    root_toml = repo_root / "pyproject.toml"
    content = root_toml.read_text(encoding="utf-8")

    # Check if already added
    if config.plugin_dir_name in content:
        console.print(
            f"[dim]  Plugin '{config.plugin_dir_name}' already in root pyproject.toml[/dim]"
        )
        return

    # Update optional-dependencies
    standalone_entry = f'{config.plugin_dir_name} = ["{config.plugin_dir_name}"]'

    # Add standalone entry before drivers-all
    content = re.sub(
        r"(drivers-all = \[)",
        f"{standalone_entry}\n\\1",
        content,
    )

    # Update drivers-all list
    drivers_all_list_pattern = r"(drivers-all = \[\s*\n)([^]]*)(\])"
    match = re.search(drivers_all_list_pattern, content)
    if match:
        before = match.group(1)
        list_content = match.group(2).strip()
        after = match.group(3)

        # Add new plugin to the list
        if list_content:
            new_list_content = f'{list_content}\n    "{config.plugin_dir_name}",'
        else:
            new_list_content = f'    "{config.plugin_dir_name}",'

        content = re.sub(
            drivers_all_list_pattern,
            rf"{before}{new_list_content}\n{after}",
            content,
        )

    # Update tool.uv.sources
    new_source = f'{config.plugin_dir_name} = {{ path = "./plugins/{config.plugin_dir_name}", editable = true }}'

    # Find the sources section
    sources_section = re.search(r"\[tool\.uv\.sources\](.*?)\n\[", content, re.DOTALL)
    if sources_section:
        section_content = sources_section.group(1)
        lines = section_content.split("\n")

        # Find the last line with editable = true
        last_editable_index = -1
        for i, line in enumerate(lines):
            if "editable = true" in line:
                last_editable_index = i

        if last_editable_index >= 0:
            lines.insert(last_editable_index + 1, new_source)
            new_section_content = "\n".join(lines)
            content = (
                content[: sources_section.start(1)]
                + new_section_content
                + content[sources_section.end(1) :]
            )

    root_toml.write_text(content, encoding="utf-8")
    console.print("[green]  ✓ Updated root pyproject.toml[/green]")


def create_plugin_scaffold(config: PluginConfig, repo_root: Path) -> None:
    """Create all files and directories for the plugin."""
    plugins_dir = repo_root / "plugins"
    plugin_dir = plugins_dir / config.plugin_dir_name
    package_dir = plugin_dir / config.plugin_dir_name.replace("-", "_")

    # Create directories
    if plugin_dir.exists():
        if not Confirm.ask(
            f"[yellow]Directory '{config.plugin_dir_name}' already exists. Overwrite?[/yellow]",
            default=False,
            console=console,
        ):
            console.print("\n[yellow]Cancelled.[/yellow]")
            raise SystemExit(0)
        shutil.rmtree(plugin_dir)

    package_dir.mkdir(parents=True)

    # Generate files
    console.print(
        f"\n[bold cyan]Creating plugin '{config.plugin_dir_name}':[/bold cyan]\n"
    )

    # driver.py
    driver_path = package_dir / "driver.py"
    driver_path.write_text(generate_driver_py(config), encoding="utf-8")
    console.print(
        f"[green]  ✓ Created[/green] [dim]{driver_path.relative_to(repo_root)}[/dim]"
    )

    # factory.py
    factory_path = package_dir / "factory.py"
    factory_path.write_text(generate_factory_py(config), encoding="utf-8")
    console.print(
        f"[green]  ✓ Created[/green] [dim]{factory_path.relative_to(repo_root)}[/dim]"
    )

    # __init__.py
    init_path = package_dir / "__init__.py"
    init_path.write_text(generate_init_py(config), encoding="utf-8")
    console.print(
        f"[green]  ✓ Created[/green] [dim]{init_path.relative_to(repo_root)}[/dim]"
    )

    # pyproject.toml
    toml_path = plugin_dir / "pyproject.toml"
    toml_path.write_text(generate_pyproject_toml(config), encoding="utf-8")
    console.print(
        f"[green]  ✓ Created[/green] [dim]{toml_path.relative_to(repo_root)}[/dim]"
    )

    # README.md
    readme_path = plugin_dir / "README.md"
    readme_content = f"""# {config.display_name} Driver Plugin

{config.display_name} driver plugin for ModLink Studio.

## Configuration

- **Device ID**: `{config.device_id}`
- **Provider**: `{config.provider}`
- **Modality**: `{config.modality}`
- **Payload Type**: `{config.payload_type}`
- **Sample Rate**: {config.sample_rate} Hz
- **Chunk Size**: {config.chunk_size}
- **Channels**: {", ".join(config.channel_names)}
{f'- **Unit**: `{config.unit}`' if config.unit else ''}

## Installation

```bash
uv sync --extra {config.plugin_dir_name}
```

## Usage

1. Open ModLink Studio
2. Go to Device page
3. Select "{config.display_name}" from the device list
4. Click "Search" to discover devices
5. Connect and start streaming

## Development

Edit `driver.py` to implement your device driver logic.
"""
    readme_path.write_text(readme_content, encoding="utf-8")
    console.print(
        f"[green]  ✓ Created[/green] [dim]{readme_path.relative_to(repo_root)}[/dim]"
    )

    # Update root pyproject.toml
    update_root_pyproject(config, repo_root)

    # Success message
    console.print("\n")
    console.print(
        Panel(
            f"[bold green]Success![/bold green]\n\n"
            f"Plugin scaffold created at:\n"
            f"[cyan]{plugin_dir.relative_to(repo_root)}[/cyan]\n\n"
            f"[bold]Next steps:[/bold]\n"
            f"1. Edit [cyan]driver.py[/cyan] to implement your driver\n"
            f"2. Run: [cyan]uv sync --extra {config.plugin_dir_name}[/cyan]\n"
            f"3. Start ModLink Studio and test",
            title="[bold green]✓ Plugin Created[/bold green]",
            border_style="green",
            padding=(1, 2),
        )
    )


def main() -> None:
    """Main entry point."""
    try:
        # Find repository root
        repo_root = Path(__file__).parent.parent
        if not (repo_root / "pyproject.toml").exists():
            console.print("[red]Error: Could not find repository root[/red]")
            raise SystemExit(1)

        # Interactive configuration
        config = prompt_for_config()

        # Create scaffold
        create_plugin_scaffold(config, repo_root)

    except KeyboardInterrupt:
        console.print("\n\n[yellow]Cancelled by user.[/yellow]")
        raise SystemExit(0)


if __name__ == "__main__":
    main()
