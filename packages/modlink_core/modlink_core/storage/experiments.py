from __future__ import annotations

from pathlib import Path
from time import time_ns
from typing import Any

from .io import read_json, write_json
from .layout import (
    SCHEMA_VERSION,
    experiment_manifest_path,
    experiments_dir,
    generate_storage_id,
    validate_storage_id,
)


class ExperimentStore:
    def __init__(self, root_dir: Path) -> None:
        self.root_dir = Path(root_dir)

    def create_experiment(
        self,
        *,
        experiment_id: str | None = None,
        display_name: str | None = None,
        metadata: dict[str, Any] | None = None,
        created_at_ns: int | None = None,
    ) -> str:
        resolved_created_at_ns = int(time_ns() if created_at_ns is None else created_at_ns)
        resolved_experiment_id = (
            generate_storage_id("exp", resolved_created_at_ns)
            if experiment_id is None
            else validate_storage_id(experiment_id, "exp")
        )
        manifest_path = experiment_manifest_path(self.root_dir, resolved_experiment_id)
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

    def read_experiment(self, experiment_id: str) -> dict[str, Any]:
        return read_json(experiment_manifest_path(self.root_dir, experiment_id))

    def write_experiment(self, experiment_id: str, payload: dict[str, Any]) -> None:
        normalized = dict(payload)
        normalized["schema_version"] = SCHEMA_VERSION
        normalized["experiment_id"] = experiment_id
        write_json(experiment_manifest_path(self.root_dir, experiment_id), normalized)

    def list_experiments(self) -> list[dict[str, Any]]:
        manifests: list[dict[str, Any]] = []
        base_dir = experiments_dir(self.root_dir)
        if not base_dir.is_dir():
            return manifests
        for path in sorted(base_dir.iterdir(), key=lambda item: item.name):
            manifest_path = path / "experiment.json"
            if manifest_path.is_file():
                manifests.append(read_json(manifest_path))
        return manifests

    def add_session_to_experiment(
        self,
        experiment_id: str,
        session_id: str,
        *,
        updated_at_ns: int | None = None,
    ) -> None:
        payload = self.read_experiment(experiment_id)
        session_ids = payload.setdefault("session_ids", [])
        if not isinstance(session_ids, list):
            raise ValueError(f"experiment '{experiment_id}' has invalid session_ids payload")
        if session_id not in session_ids:
            session_ids.append(session_id)
        payload["updated_at_ns"] = int(time_ns() if updated_at_ns is None else updated_at_ns)
        self.write_experiment(experiment_id, payload)
