from __future__ import annotations

from pathlib import Path

from platformdirs import user_documents_path

from ..settings import SettingsGroup, SettingsStore, SettingsStr

STORAGE_ROOT_DIR_KEY = "storage.root_dir"
EXPORT_ROOT_DIR_KEY = "storage.export_root_dir"


class StorageSettings:
    def __init__(self, settings: SettingsStore) -> None:
        self._store = settings
        self._ensure_declared()
        self._settings = settings.storage

    @property
    def storage_root_dir(self) -> Path | None:
        return _decode_optional_path(self._settings.root_dir.value)

    @property
    def export_root_dir(self) -> Path | None:
        return _decode_optional_path(self._settings.export_root_dir.value)

    def set_storage_root_dir(self, path: str | Path | None, *, persist: bool = True) -> None:
        self._settings.root_dir = _encode_optional_path(path)
        if persist:
            self._store.save()

    def set_export_root_dir(self, path: str | Path | None, *, persist: bool = True) -> None:
        self._settings.export_root_dir = _encode_optional_path(path)
        if persist:
            self._store.save()

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

    def _ensure_declared(self) -> None:
        try:
            storage = self._store.storage
        except AttributeError:
            self._store.add(storage=SettingsGroup())
            storage = self._store.storage

        if not _has_declared_child(storage, "root_dir"):
            storage.add(root_dir=SettingsStr(default=""))
        if not _has_declared_child(storage, "export_root_dir"):
            storage.add(export_root_dir=SettingsStr(default=""))


def default_storage_root_dir() -> Path:
    documents_dir = user_documents_path()
    if documents_dir:
        return Path(documents_dir) / "ModLink Studio" / "data"
    return Path.home() / "ModLink Studio" / "data"


def _has_declared_child(node: object, name: str) -> bool:
    try:
        getattr(node, name)
    except AttributeError:
        return False
    return True


def _encode_optional_path(path: str | Path | None) -> str:
    if path is None:
        return ""
    return str(Path(path).expanduser())


def _decode_optional_path(value: object) -> Path | None:
    if not isinstance(value, str):
        raise TypeError("storage path setting must be a string")
    if value == "":
        return None
    return Path(value).expanduser()


__all__ = [
    "EXPORT_ROOT_DIR_KEY",
    "STORAGE_ROOT_DIR_KEY",
    "StorageSettings",
    "default_storage_root_dir",
]
