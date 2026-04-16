from __future__ import annotations

import json

import pytest

from modlink_core.settings import SettingsBool, SettingsGroup, SettingsInt, SettingsStore


def _build_settings(path):
    settings = SettingsStore(path=path)
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
    with pytest.raises(ValueError, match="min 8000"):
        settings.load()


def test_store_requires_path_for_save_and_load() -> None:
    settings = SettingsStore()
    settings.add(ui=SettingsGroup(preview=SettingsGroup(sample_rate=SettingsInt(default=48_000))))

    with pytest.raises(ValueError, match="path is required"):
        settings.save()

    with pytest.raises(ValueError, match="path is required"):
        settings.load()
