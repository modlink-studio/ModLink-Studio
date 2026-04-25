"""Workspace safety and file application helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class FileEdit:
    path: str
    content: str


def parse_file_edits(payload: object) -> list[FileEdit]:
    if not isinstance(payload, dict):
        raise ValueError("AI edit payload must be an object")
    raw_files = payload.get("files")
    if not isinstance(raw_files, list):
        raise ValueError("AI edit payload must contain a files array")
    edits: list[FileEdit] = []
    for raw_file in raw_files:
        if not isinstance(raw_file, dict):
            raise ValueError("Each file edit must be an object")
        path = raw_file.get("path")
        content = raw_file.get("content")
        if not isinstance(path, str) or not path.strip():
            raise ValueError("Each file edit requires a non-empty path")
        if not isinstance(content, str):
            raise ValueError(f"File edit {path!r} requires string content")
        edits.append(FileEdit(path=path.strip(), content=content))
    return edits


def apply_file_edits(project_dir: Path, plugin_name: str, edits: list[FileEdit]) -> list[Path]:
    root = project_dir.resolve()
    plugin_package = plugin_name.replace("-", "_")
    written: list[Path] = []
    for edit in edits:
        relative_path = Path(edit.path)
        _validate_relative_path(relative_path)
        if not _is_allowed_project_file(relative_path, plugin_package):
            raise ValueError(f"AI edit is not allowed to modify {edit.path!r}")
        target = (root / relative_path).resolve()
        if not _is_relative_to(target, root):
            raise ValueError(f"AI edit escapes the project directory: {edit.path!r}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(edit.content, encoding="utf-8")
        written.append(target)
    return written


def summarize_project_files(project_dir: Path, *, max_chars: int = 18000) -> str:
    root = project_dir.resolve()
    parts: list[str] = []
    for path in _important_files(root):
        if not path.exists() or not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        content = path.read_text(encoding="utf-8", errors="replace")
        parts.append(f"--- {relative} ---\n{content}")
        if sum(len(part) for part in parts) >= max_chars:
            break
    text = "\n\n".join(parts)
    return text[:max_chars]


def _important_files(root: Path) -> list[Path]:
    files = [root / "pyproject.toml", root / "README.md"]
    for child in sorted(root.iterdir()):
        if child.is_dir() and child.name not in {".venv", "tests", "__pycache__"}:
            files.extend(sorted(child.glob("*.py")))
    tests = root / "tests"
    if tests.exists():
        files.extend(sorted(tests.glob("*.py")))
    return files


def _validate_relative_path(path: Path) -> None:
    if path.is_absolute():
        raise ValueError(f"AI edit path must be relative: {path}")
    if any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"AI edit path cannot contain empty, dot, or parent parts: {path}")


def _is_allowed_project_file(path: Path, plugin_package: str) -> bool:
    parts = path.parts
    if len(parts) == 1 and parts[0] in {"README.md", "pyproject.toml"}:
        return True
    if len(parts) >= 2 and parts[0] == "tests" and path.suffix == ".py":
        return True
    if len(parts) >= 2 and parts[0] == plugin_package and path.suffix == ".py":
        return True
    return False


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def normalize_json_object(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object")
    return value
