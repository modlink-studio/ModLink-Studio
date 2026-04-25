"""Local .env loading for plugin-agent development."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import dotenv_values


def load_agent_env(*, cwd: Path | None = None) -> None:
    """Load local .env files without overriding real environment variables."""

    protected_keys = set(os.environ)
    root = Path(__file__).resolve().parents[1]
    working_dir = Path.cwd() if cwd is None else cwd
    paths = [root / ".env", working_dir / ".env"]
    seen: set[Path] = set()
    for path in paths:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        for key, value in dotenv_values(resolved).items():
            if value is None or key in protected_keys:
                continue
            os.environ[key] = value
