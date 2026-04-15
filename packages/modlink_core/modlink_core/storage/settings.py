from __future__ import annotations

from pathlib import Path

from platformdirs import user_documents_path

from ..settings import SettingsSpec, SettingsStore, path_setting

STORAGE_ROOT_DIR_KEY = "storage.root_dir"
EXPORT_ROOT_DIR_KEY = "export.root_dir"

_STORAGE_SETTINGS_SPEC = SettingsSpec(
    namespace="storage",
    schema={
        "root_dir": path_setting(),
        "export_root_dir": path_setting(),
    },
)


class StorageSettings:
    def __init__(self, settings: SettingsStore) -> None:
        self._store = settings.bind(_STORAGE_SETTINGS_SPEC)

    @property
    def storage_root_dir(self) -> Path | None:
        return self._store.root_dir

    @property
    def export_root_dir(self) -> Path | None:
        return self._store.export_root_dir

    def set_storage_root_dir(self, path: str | Path | None, *, persist: bool = True) -> None:
        self._store.set("root_dir", path, persist=persist)

    def set_export_root_dir(self, path: str | Path | None, *, persist: bool = True) -> None:
        self._store.set("export_root_dir", path, persist=persist)

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
