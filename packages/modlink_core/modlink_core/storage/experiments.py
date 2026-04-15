from __future__ import annotations

from pathlib import Path
from time import time_ns
from typing import Any

from ._internal.files import read_json, write_json
from ._internal.ids import (
    SCHEMA_VERSION,
    generate_storage_id,
    validate_storage_id,
)


def create_experiment(
    root_dir: Path,
    *,
    experiment_id: str | None = None,
    display_name: str | None = None,
    metadata: dict[str, Any] | None = None,
    created_at_ns: int | None = None,
) -> str:
    root_dir = Path(root_dir)
    resolved_created_at_ns = int(time_ns() if created_at_ns is None else created_at_ns)
    resolved_experiment_id = (
        generate_storage_id("exp", resolved_created_at_ns)
        if experiment_id is None
        else validate_storage_id(experiment_id, "exp")
    )
    manifest_path = root_dir / "experiments" / resolved_experiment_id / "experiment.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=False)
    write_json(
        manifest_path,
        {
            "schema_version": SCHEMA_VERSION,
            "experiment_id": resolved_experiment_id,
            "display_name": display_name,
            "created_at_ns": resolved_created_at_ns,
            "updated_at_ns": resolved_created_at_ns,
            "session_ids": [],
            "metadata": {} if metadata is None else dict(metadata),
        },
    )
    return resolved_experiment_id


def read_experiment(root_dir: Path, experiment_id: str) -> dict[str, Any]:
    return read_json(Path(root_dir) / "experiments" / experiment_id / "experiment.json")


def list_experiments(root_dir: Path) -> list[dict[str, Any]]:
    manifests: list[dict[str, Any]] = []
    base_dir = Path(root_dir) / "experiments"
    if not base_dir.is_dir():
        return manifests
    for path in sorted(base_dir.iterdir(), key=lambda item: item.name):
        manifest_path = path / "experiment.json"
        if manifest_path.is_file():
            manifests.append(read_json(manifest_path))
    return manifests


def add_session_to_experiment(
    root_dir: Path,
    experiment_id: str,
    session_id: str,
    *,
    updated_at_ns: int | None = None,
) -> None:
    root_dir = Path(root_dir)
    payload = read_experiment(root_dir, experiment_id)
    session_ids = payload.setdefault("session_ids", [])
    if not isinstance(session_ids, list):
        raise ValueError(f"experiment '{experiment_id}' has invalid session_ids payload")
    if session_id not in session_ids:
        session_ids.append(session_id)
    payload["updated_at_ns"] = int(time_ns() if updated_at_ns is None else updated_at_ns)
    payload["schema_version"] = SCHEMA_VERSION
    payload["experiment_id"] = experiment_id
    write_json(root_dir / "experiments" / experiment_id / "experiment.json", payload)
