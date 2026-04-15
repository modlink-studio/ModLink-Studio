from __future__ import annotations

from pathlib import Path

from platformdirs import user_documents_path

from ..settings import PathField

STORAGE_ROOT_DIR_KEY = "storage.root_dir"
EXPORT_ROOT_DIR_KEY = "export.root_dir"


class StorageSettings:
    storage_root_dir = PathField(STORAGE_ROOT_DIR_KEY)
    export_root_dir = PathField(EXPORT_ROOT_DIR_KEY)

    def __init__(self, settings: object) -> None:
        self._settings = settings

    def set_storage_root_dir(self, path: str | Path | None, *, persist: bool = True) -> None:
        type(self).storage_root_dir.set_value(self, path, persist=persist)

    def set_export_root_dir(self, path: str | Path | None, *, persist: bool = True) -> None:
        type(self).export_root_dir.set_value(self, path, persist=persist)

    def resolved_storage_root_dir(self) -> Path:
        configured = self.storage_root_dir
        if configured is not None:
            return configured
        return default_storage_root_dir()

    def resolved_export_root_dir(self) -> Path:
        configured = self.export_root_dir
        if configured is not None:
            return configured
        return self.resolved_storage_root_dir() / "exports"

    def recordings_dir(self) -> Path:
        return self.resolved_storage_root_dir() / "recordings"

    def sessions_dir(self) -> Path:
        return self.resolved_storage_root_dir() / "sessions"

    def experiments_dir(self) -> Path:
        return self.resolved_storage_root_dir() / "experiments"

    def exports_dir(self) -> Path:
        return self.resolved_export_root_dir()


def default_storage_root_dir() -> Path:
    documents_dir = user_documents_path()
    if documents_dir:
        return Path(documents_dir) / "ModLink Studio" / "data"
    return Path.home() / "ModLink Studio" / "data"


__all__ = [
    "EXPORT_ROOT_DIR_KEY",
    "STORAGE_ROOT_DIR_KEY",
    "StorageSettings",
    "default_storage_root_dir",
]
