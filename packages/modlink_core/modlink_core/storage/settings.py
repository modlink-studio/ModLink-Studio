from __future__ import annotations

from pathlib import Path

from platformdirs import user_documents_path

STORAGE_ROOT_DIR_KEY = "storage.root_dir"
EXPORT_ROOT_DIR_KEY = "storage.export_root_dir"


def default_storage_root_dir() -> Path:
    documents_dir = user_documents_path()
    if documents_dir:
        return Path(documents_dir) / "ModLink Studio" / "data"
    return Path.home() / "ModLink Studio" / "data"


def resolved_storage_root_dir(settings: object) -> Path:
    configured = _read_optional_path(settings, "root_dir")
    if configured is not None:
        return configured
    return default_storage_root_dir()


def resolved_export_root_dir(settings: object) -> Path:
    configured = _read_optional_path(settings, "export_root_dir")
    if configured is not None:
        return configured
    return resolved_storage_root_dir(settings) / "exports"


def _read_optional_path(settings: object, name: str) -> Path | None:
    try:
        storage = getattr(settings, "storage")
    except AttributeError:
        return None
    try:
        item = getattr(storage, name)
    except AttributeError:
        return None

    value = item.value
    if not isinstance(value, str):
        raise TypeError(f"storage.{name} must be a string")
    if value == "":
        return None
    return Path(value).expanduser()
