"""CLI entry point for the ModLink plugin AI agent."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import typer
from rich.console import Console

from .agent import PluginAgent, PluginAgentConfig, PluginAgentResult
from .client import AiConfig, OpenAICompatibleJsonClient
from .env import load_agent_env

app = typer.Typer(
    name="modlink-plugin-agent",
    help=(
        "Python-only AI agent for generating ModLink driver plugins. It uses an internal "
        "deterministic scaffold writer, then asks an OpenAI-compatible model to fill in "
        "driver code, README content, and tests. AI config can come from options, environment "
        "variables, or local .env files. Examples: modlink-plugin-agent generate "
        '"serial two-channel pressure sensor" --out ./plugins; '
        'modlink-plugin-agent generate "生成串口双通道压力传感器插件" --out ./plugins'
    ),
)
console = Console()


@app.callback()
def _main() -> None:
    """Use generate to create a driver plugin from a device description."""


@app.command()
def generate(
    description: str = typer.Argument(..., help="Natural-language device/plugin description."),
    out: Path = typer.Option(
        ..., "--out", "-o", help="Directory that will contain the plugin project."
    ),
    base_url: str | None = typer.Option(
        None,
        "--base-url",
        help="OpenAI-compatible base URL. Defaults to MODLINK_AI_BASE_URL.",
    ),
    model: str | None = typer.Option(
        None,
        "--model",
        help="Chat model name. Defaults to MODLINK_AI_MODEL.",
    ),
    api_key_env: str = typer.Option(
        "MODLINK_AI_API_KEY",
        "--api-key-env",
        help="Environment variable that contains the API key.",
    ),
    timeout_s: float = typer.Option(
        180.0,
        "--timeout-s",
        min=1.0,
        help="Per-request AI service timeout in seconds.",
    ),
    max_repairs: int = typer.Option(2, "--max-repairs", min=0, help="Maximum AI repair attempts."),
    overwrite: bool = typer.Option(
        False, "--overwrite", help="Overwrite an existing plugin project."
    ),
    json_output: bool = typer.Option(False, "--json", help="Print machine-readable JSON result."),
) -> None:
    """Generate, verify, and repair a ModLink driver plugin project."""

    load_agent_env()
    resolved_base_url = (base_url or os.environ.get("MODLINK_AI_BASE_URL", "")).strip()
    resolved_model = (model or os.environ.get("MODLINK_AI_MODEL", "")).strip()
    api_key = os.environ.get(api_key_env, "").strip()
    if not resolved_base_url or not resolved_model or not api_key:
        typer.echo(
            "Missing AI configuration. Provide --base-url/--model and set the API key env var "
            f"{api_key_env}, or set MODLINK_AI_BASE_URL, MODLINK_AI_MODEL, and MODLINK_AI_API_KEY."
        )
        raise typer.Exit(1)

    client = OpenAICompatibleJsonClient(
        AiConfig(
            base_url=resolved_base_url,
            api_key=api_key,
            model=resolved_model,
            timeout_s=timeout_s,
        )
    )
    agent = PluginAgent(
        client=client,
        config=PluginAgentConfig(
            out_dir=out.resolve(),
            overwrite=overwrite,
            max_repairs=max_repairs,
        ),
    )

    try:
        result = agent.generate(description)
    except (RuntimeError, ValueError) as exc:
        error = str(exc)
        if json_output:
            console.print_json(data={"ok": False, "error": error})
        else:
            console.print(f"[red]{error}[/red]")
        raise typer.Exit(1) from None

    if json_output:
        console.print_json(data=_result_to_json(result))
    else:
        _print_result(result)
    if not result.ok:
        raise typer.Exit(1)


def _print_result(result: PluginAgentResult) -> None:
    if result.ok:
        console.print("[green]Plugin generated and verified.[/green]")
    else:
        console.print("[red]Plugin generation finished, but verification failed.[/red]")
    console.print(f"Project: {result.project_dir}")
    console.print(f"Repairs: {result.repairs}")
    if result.written_files:
        console.print("AI-written files:")
        for path in result.written_files:
            console.print(f"  - {path}")
    if result.verification_log:
        console.print("\nVerification log:")
        console.print(result.verification_log[-4000:])


def _result_to_json(result: PluginAgentResult) -> dict[str, Any]:
    return {
        "ok": result.ok,
        "project_dir": str(result.project_dir),
        "repairs": result.repairs,
        "written_files": [str(path) for path in result.written_files],
        "scaffold_spec": result.scaffold_spec,
        "verification_log": result.verification_log,
        "error": result.error,
    }


def main(argv: list[str] | None = None) -> int:
    try:
        app(argv)
    except typer.Exit as exc:
        return int(exc.exit_code)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
