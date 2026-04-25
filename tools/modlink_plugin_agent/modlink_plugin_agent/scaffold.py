"""Bridge to the deterministic npm scaffold tool."""

from __future__ import annotations

import json
import shlex
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

type CommandRunner = Callable[..., subprocess.CompletedProcess[str]]


def default_scaffold_command(cwd: Path | None = None) -> list[str]:
    root = _find_repo_root(Path.cwd() if cwd is None else cwd)
    if root is not None and (root / "tools" / "modlink_plugin_scaffold" / "package.json").exists():
        return ["npm", "--workspace", "@modlink-studio/plugin-scaffold", "run", "dev", "--"]
    return ["npx", "@modlink-studio/plugin-scaffold"]


def run_scaffold_generate(
    spec: dict[str, Any],
    out_dir: Path,
    *,
    scaffold_command: str | Sequence[str] | None = None,
    overwrite: bool = False,
    runner: CommandRunner = subprocess.run,
) -> dict[str, Any]:
    command = _normalize_command(scaffold_command)
    args = [
        *command,
        "generate",
        "--stdin",
        "--json",
        "--out",
        str(out_dir),
    ]
    if overwrite:
        args.append("--overwrite")
    result = runner(
        args,
        input=json.dumps(spec),
        text=True,
        capture_output=True,
        check=False,
    )
    stdout = result.stdout.strip()
    if not stdout:
        raise RuntimeError(f"scaffold produced no JSON output: {result.stderr.strip()}")
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"scaffold returned invalid JSON: {stdout}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("scaffold JSON output must be an object")
    if result.returncode != 0 or not payload.get("ok"):
        message = payload.get("message") if isinstance(payload.get("message"), str) else ""
        detail = message or result.stderr.strip() or stdout
        raise RuntimeError(f"scaffold failed: {detail}")
    return payload


def _normalize_command(command: str | Sequence[str] | None) -> list[str]:
    if command is None:
        return default_scaffold_command()
    if isinstance(command, str):
        parts = shlex.split(command, posix=False)
        if not parts:
            raise ValueError("scaffold command must not be empty")
        return parts
    parts = [str(part) for part in command if str(part)]
    if not parts:
        raise ValueError("scaffold command must not be empty")
    return parts


def _find_repo_root(start: Path) -> Path | None:
    for candidate in [start.resolve(), *start.resolve().parents]:
        if (candidate / "package.json").exists() and (candidate / "pyproject.toml").exists():
            return candidate
    return None
