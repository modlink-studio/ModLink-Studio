from __future__ import annotations

import json
from pathlib import Path

import pytest

from modlink_core.settings import (
    SettingsStore,
    SettingsSpec,
    bool_setting,
    int_setting,
    path_setting,
)


def _build_demo_view(path):
    settings = SettingsStore(path=path)
    view = settings.bind(
        SettingsSpec(
            namespace="demo",
            schema={
                "sample_rate_hz": int_setting(default=30),
                "storage": {
                    "root_dir": path_setting(),
                },
                "enabled": bool_setting(default=False),
            },
        )
    )
    return settings, view


def test_setting_fields_use_defaults_when_keys_are_missing(tmp_path) -> None:
    settings, demo = _build_demo_view(tmp_path / "settings.json")

    assert demo.sample_rate_hz == 30
    assert demo.enabled is False


def test_settings_load_existing_payload_into_view(tmp_path) -> None:
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps(
            {
                "demo": {
                    "sample_rate_hz": 60,
                    "enabled": True,
                    "storage": {"root_dir": "~/loaded-data"},
                }
            }
        ),
        encoding="utf-8",
    )
    settings, demo = _build_demo_view(settings_path)

    assert demo.sample_rate_hz == 60
    assert demo.enabled is True
    assert demo.storage.root_dir == Path("~/loaded-data").expanduser()


def test_field_assignment_only_updates_memory_until_save(tmp_path) -> None:
    settings, demo = _build_demo_view(tmp_path / "settings.json")

    demo.sample_rate_hz = 120
    demo.enabled = True
    demo.storage.root_dir = "~/modlink-data"

    assert not (tmp_path / "settings.json").exists()
    assert demo.sample_rate_hz == 120
    assert demo.enabled is True
    assert demo.storage.root_dir == Path("~/modlink-data").expanduser()


def test_save_writes_current_values_to_disk(tmp_path) -> None:
    settings, demo = _build_demo_view(tmp_path / "settings.json")

    demo.sample_rate_hz = 120
    demo.enabled = True
    demo.storage.root_dir = tmp_path / "data"
    settings.save()

    payload = json.loads((tmp_path / "settings.json").read_text(encoding="utf-8"))
    assert payload == {
        "demo": {
            "sample_rate_hz": 120,
            "enabled": True,
            "storage": {"root_dir": str(tmp_path / "data")},
        }
    }


def test_path_field_treats_empty_payload_as_unset(tmp_path) -> None:
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps({"demo": {"storage": {"root_dir": "   "}}}),
        encoding="utf-8",
    )
    settings, demo = _build_demo_view(settings_path)

    assert demo.storage.root_dir is None


def test_path_field_can_be_unset_after_save(tmp_path) -> None:
    settings_path = tmp_path / "settings.json"
    settings, demo = _build_demo_view(settings_path)
    demo.storage.root_dir = tmp_path / "data"
    settings.save()

    demo.storage.root_dir = None
    payload_before_save = json.loads((tmp_path / "settings.json").read_text(encoding="utf-8"))
    assert payload_before_save["demo"]["storage"]["root_dir"] == str(tmp_path / "data")

    settings.save()

    payload_after_save = json.loads((tmp_path / "settings.json").read_text(encoding="utf-8"))
    assert payload_after_save == {}


def test_path_field_rejects_blank_strings(tmp_path) -> None:
    settings, demo = _build_demo_view(tmp_path / "settings.json")
    with pytest.raises(ValueError, match="must not be empty"):
        demo.storage.root_dir = "  "
