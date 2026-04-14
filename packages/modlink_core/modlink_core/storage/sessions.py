from __future__ import annotations

from pathlib import Path
from time import time_ns
from typing import Any

from .io import read_json, write_json
from .layout import (
    SCHEMA_VERSION,
    generate_storage_id,
    session_manifest_path,
    sessions_dir,
    validate_storage_id,
)


class SessionStore:
    def __init__(self, root_dir: Path) -> None:
        self.root_dir = Path(root_dir)

    def create_session(
        self,
        *,
        session_id: str | None = None,
        display_name: str | None = None,
        metadata: dict[str, Any] | None = None,
        created_at_ns: int | None = None,
    ) -> str:
        resolved_created_at_ns = int(time_ns() if created_at_ns is None else created_at_ns)
        resolved_session_id = (
            generate_storage_id("ses", resolved_created_at_ns)
            if session_id is None
            else validate_storage_id(session_id, "ses")
        )
        manifest_path = session_manifest_path(self.root_dir, resolved_session_id)
        manifest_path.parent.mkdir(parents=True, exist_ok=False)
        write_json(
            manifest_path,
            {
                "schema_version": SCHEMA_VERSION,
                "session_id": resolved_session_id,
                "display_name": display_name,
                "created_at_ns": resolved_created_at_ns,
                "updated_at_ns": resolved_created_at_ns,
                "recording_ids": [],
                "metadata": {} if metadata is None else dict(metadata),
            },
        )
        return resolved_session_id

    def read_session(self, session_id: str) -> dict[str, Any]:
        return read_json(session_manifest_path(self.root_dir, session_id))

    def write_session(self, session_id: str, payload: dict[str, Any]) -> None:
        normalized = dict(payload)
        normalized["schema_version"] = SCHEMA_VERSION
        normalized["session_id"] = session_id
        write_json(session_manifest_path(self.root_dir, session_id), normalized)

    def list_sessions(self) -> list[dict[str, Any]]:
        manifests: list[dict[str, Any]] = []
        base_dir = sessions_dir(self.root_dir)
        if not base_dir.is_dir():
            return manifests
        for path in sorted(base_dir.iterdir(), key=lambda item: item.name):
            manifest_path = path / "session.json"
            if manifest_path.is_file():
                manifests.append(read_json(manifest_path))
        return manifests

    def add_recording_to_session(
        self,
        session_id: str,
        recording_id: str,
        *,
        updated_at_ns: int | None = None,
    ) -> None:
        payload = self.read_session(session_id)
        recording_ids = payload.setdefault("recording_ids", [])
        if not isinstance(recording_ids, list):
            raise ValueError(f"session '{session_id}' has invalid recording_ids payload")
        if recording_id not in recording_ids:
            recording_ids.append(recording_id)
        payload["updated_at_ns"] = int(time_ns() if updated_at_ns is None else updated_at_ns)
        self.write_session(session_id, payload)
