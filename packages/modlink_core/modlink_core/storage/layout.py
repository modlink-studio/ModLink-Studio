from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

SCHEMA_VERSION = 1


def recordings_dir(root_dir: Path) -> Path:
    return Path(root_dir) / "recordings"


def recording_dir(root_dir: Path, recording_id: str) -> Path:
    return recordings_dir(root_dir) / recording_id


def recording_manifest_path(root_dir: Path, recording_id: str) -> Path:
    return recording_dir(root_dir, recording_id) / "recording.json"


def sessions_dir(root_dir: Path) -> Path:
    return Path(root_dir) / "sessions"


def session_dir(root_dir: Path, session_id: str) -> Path:
    return sessions_dir(root_dir) / session_id


def session_manifest_path(root_dir: Path, session_id: str) -> Path:
    return session_dir(root_dir, session_id) / "session.json"


def experiments_dir(root_dir: Path) -> Path:
    return Path(root_dir) / "experiments"


def experiment_dir(root_dir: Path, experiment_id: str) -> Path:
    return experiments_dir(root_dir) / experiment_id


def experiment_manifest_path(root_dir: Path, experiment_id: str) -> Path:
    return experiment_dir(root_dir, experiment_id) / "experiment.json"


def safe_path_component(value: str) -> str:
    normalized = re.sub(r'[<>:"/\\\\|?*]+', "_", str(value).strip())
    normalized = normalized.rstrip(". ")
    return normalized or "_"


def generate_storage_id(prefix: str, timestamp_ns: int) -> str:
    timestamp = datetime.fromtimestamp(timestamp_ns / 1_000_000_000, tz=UTC)
    return f"{prefix}_{timestamp.strftime('%Y%m%dT%H%M%S')}_{timestamp_ns % 1_000_000_000:09d}Z"


def validate_storage_id(value: str, prefix: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{prefix}_id must not be empty")
    if safe_path_component(normalized) != normalized:
        raise ValueError(f"{prefix}_id contains unsupported path characters")
    return normalized
