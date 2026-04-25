"""Deterministic verification for generated plugin projects."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

type CommandRunner = Callable[..., subprocess.CompletedProcess[str]]


@dataclass(frozen=True, slots=True)
class VerificationResult:
    ok: bool
    log: str


def verify_plugin_project(
    project_dir: Path,
    *,
    runner: CommandRunner = subprocess.run,
    timeout_s: float = 180.0,
) -> VerificationResult:
    root = project_dir.resolve()
    venv_dir = root / ".venv"
    python = _venv_python(venv_dir)
    commands = [
        [sys.executable, "-m", "venv", str(venv_dir)],
        [str(python), "-m", "pip", "install", "-e", _local_sdk_path(root)]
        if _local_sdk_path(root) is not None
        else None,
        [str(python), "-m", "pip", "install", "-e", ".", "pytest"],
        [str(python), "-m", "compileall", "."],
        [str(python), "-m", "pytest"],
    ]

    logs: list[str] = []
    for command in commands:
        if command is None:
            continue
        result = runner(
            [str(part) for part in command],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_s,
        )
        logs.append(_format_command_log(command, result))
        if result.returncode != 0:
            return VerificationResult(False, "\n\n".join(logs)[-12000:])
    return VerificationResult(True, "\n\n".join(logs)[-12000:])


def _venv_python(venv_dir: Path) -> Path:
    if sys.platform == "win32":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _local_sdk_path(project_dir: Path) -> str | None:
    for candidate in [project_dir, *project_dir.parents]:
        sdk_path = candidate / "packages" / "modlink_sdk"
        if (sdk_path / "pyproject.toml").exists():
            return str(sdk_path)
    return None


def _format_command_log(command: list[object], result: subprocess.CompletedProcess[str]) -> str:
    command_text = " ".join(str(part) for part in command)
    return (
        f"$ {command_text}\n"
        f"exit={result.returncode}\n"
        f"stdout:\n{result.stdout.strip()}\n"
        f"stderr:\n{result.stderr.strip()}"
    )
