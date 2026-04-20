from __future__ import annotations

import json

import pytest

from modlink_core.settings import (
    SettingsBool,
    SettingsGroup,
    SettingsInt,
    SettingsStore,
    declare_core_settings,
)
from modlink_core.storage import (
    default_storage_root_dir,
    resolved_export_root_dir,
    resolved_storage_root_dir,
)


def _build_settings(path):
    settings = SettingsStore(path=path)
    settings.add(
        ui=SettingsGroup(
            labels=SettingsGroup(enabled=SettingsBool(default=False)),
            preview=SettingsGroup(sample_rate=SettingsInt(default=48_000, min=8_000, max=192_000)),
        )
    )
    return settings


def _build_settings_with_events(path, events: list[tuple[str, object]]):
    settings = SettingsStore(path=path, on_change=lambda key, value: events.append((key, value)))
    settings.add(
        ui=SettingsGroup(
            labels=SettingsGroup(enabled=SettingsBool(default=False)),
            preview=SettingsGroup(sample_rate=SettingsInt(default=48_000, min=8_000, max=192_000)),
        )
    )
    return settings


def test_save_writes_full_snapshot_payload_with_version(tmp_path) -> None:
    path = tmp_path / "settings.json"
    settings = _build_settings(path)

    settings.save()

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload == {
        "_version": 1,
        "values": {
            "ui": {
                "labels": {"enabled": False},
                "preview": {"sample_rate": 48_000},
            }
        },
    }


def test_load_applies_values_into_existing_tree(tmp_path) -> None:
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps(
            {
                "_version": 1,
                "values": {
                    "ui": {
                        "labels": {"enabled": True},
                        "preview": {"sample_rate": 44_100},
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    settings = _build_settings(path)

    settings.load()

    assert settings.ui.labels.enabled.value is True
    assert settings.ui.preview.sample_rate.value == 44_100


def test_direct_assignment_emits_leaf_change_event(tmp_path) -> None:
    events: list[tuple[str, object]] = []
    settings = _build_settings_with_events(tmp_path / "settings.json", events)

    settings.ui.preview.sample_rate = 44_100

    assert events == [("ui.preview.sample_rate", 44_100)]


def test_load_emits_leaf_change_events_for_changed_values(tmp_path) -> None:
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps(
            {
                "_version": 1,
                "values": {
                    "ui": {
                        "labels": {"enabled": True},
                        "preview": {"sample_rate": 44_100},
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    events: list[tuple[str, object]] = []
    settings = _build_settings_with_events(path, events)

    settings.load()

    assert sorted(events) == [
        ("ui.labels.enabled", True),
        ("ui.preview.sample_rate", 44_100),
    ]


def test_load_restores_missing_keys_to_defaults(tmp_path) -> None:
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps(
            {
                "_version": 1,
                "values": {
                    "ui": {
                        "labels": {"enabled": True},
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    settings = _build_settings(path)
    settings.ui.preview.sample_rate = 44_100

    settings.load()

    assert settings.ui.labels.enabled.value is True
    assert settings.ui.preview.sample_rate.value == 48_000


def test_load_rejects_unknown_keys_and_invalid_values(tmp_path) -> None:
    path = tmp_path / "settings.json"
    settings = _build_settings(path)

    path.write_text(
        json.dumps(
            {
                "_version": 1,
                "values": {
                    "ui": {
                        "preview": {
                            "unknown": 1,
                        }
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(KeyError, match="unknown key in file: ui.preview.unknown"):
        settings.load()

    settings.ui.preview.sample_rate = 44_100
    path.write_text(
        json.dumps(
            {
                "_version": 1,
                "values": {
                    "ui": {
                        "preview": {
                            "sample_rate": 1,
                        }
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match=r"ui\.preview\.sample_rate: value 1 < min 8000"):
        settings.load()
    assert settings.ui.preview.sample_rate.value == 44_100


def test_load_rejects_version_mismatch_without_mutating_state(tmp_path) -> None:
    path = tmp_path / "settings.json"
    settings = _build_settings(path)
    settings.ui.preview.sample_rate = 44_100

    path.write_text(
        json.dumps(
            {
                "_version": 2,
                "values": {
                    "ui": {
                        "labels": {"enabled": True},
                        "preview": {"sample_rate": 96_000},
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="settings version mismatch: file=2, expected=1"):
        settings.load()

    assert settings.ui.preview.sample_rate.value == 44_100


def test_store_requires_path_for_save_and_load() -> None:
    settings = SettingsStore()
    settings.add(ui=SettingsGroup(preview=SettingsGroup(sample_rate=SettingsInt(default=48_000))))

    with pytest.raises(ValueError, match="path is required"):
        settings.save()

    with pytest.raises(ValueError, match="path is required"):
        settings.load()


def test_declare_core_settings_is_idempotent_and_resolves_declared_paths(tmp_path) -> None:
    settings = SettingsStore(path=tmp_path / "settings.json")

    declare_core_settings(settings)
    declare_core_settings(settings)
    settings.storage.root_dir = str(tmp_path / "data")
    settings.storage.export_root_dir = str(tmp_path / "exports")

    assert settings.snapshot()["storage"] == {
        "root_dir": str(tmp_path / "data"),
        "export_root_dir": str(tmp_path / "exports"),
    }
    assert resolved_storage_root_dir(settings) == tmp_path / "data"
    assert resolved_export_root_dir(settings) == tmp_path / "exports"


def test_declare_core_settings_declares_core_owned_storage_group(tmp_path) -> None:
    settings = SettingsStore(path=tmp_path / "settings.json")

    declare_core_settings(settings)
    settings.storage.root_dir = str(tmp_path / "core-data")

    assert resolved_storage_root_dir(settings) == tmp_path / "core-data"


def test_storage_path_resolution_uses_defaults_without_declaring_storage_group(tmp_path) -> None:
    events: list[tuple[str, object]] = []
    settings = SettingsStore(
        path=tmp_path / "settings.json",
        on_change=lambda key, value: events.append((key, value)),
    )

    assert resolved_storage_root_dir(settings) == default_storage_root_dir()
    assert resolved_export_root_dir(settings) == default_storage_root_dir() / "exports"
    assert events == []
    with pytest.raises(AttributeError, match="unknown key: storage"):
        _ = settings.storage
