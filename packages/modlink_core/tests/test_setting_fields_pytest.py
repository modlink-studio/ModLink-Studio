from __future__ import annotations

import json
from pathlib import Path

from modlink_core.settings import PathField, SettingField, Settings


class DemoSettings(Settings):
    sample_rate_hz = SettingField("demo.sample_rate_hz", default=30)
    storage_root_dir = PathField("demo.storage.root_dir")
    enabled = SettingField("demo.enabled", default=False)


def test_setting_field_uses_default_when_key_is_missing(tmp_path) -> None:
    demo = DemoSettings(path=tmp_path / "settings.json")

    assert demo.sample_rate_hz == 30
    assert demo.enabled is False


def test_settings_load_existing_payload_into_fields(tmp_path) -> None:
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
    demo = DemoSettings(path=settings_path)

    assert demo.sample_rate_hz == 60
    assert demo.enabled is True
    assert demo.storage_root_dir == Path("~/loaded-data").expanduser()


def test_field_assignment_only_updates_memory_until_save(tmp_path) -> None:
    settings_path = tmp_path / "settings.json"
    demo = DemoSettings(path=settings_path)

    demo.sample_rate_hz = 120
    demo.enabled = True
    demo.storage_root_dir = "~/modlink-data"

    assert settings_path.exists() is False
    assert demo.sample_rate_hz == 120
    assert demo.enabled is True
    assert demo.storage_root_dir == Path("~/modlink-data").expanduser()


def test_save_writes_current_field_values_to_disk(tmp_path) -> None:
    settings_path = tmp_path / "settings.json"
    demo = DemoSettings(path=settings_path)

    demo.sample_rate_hz = 120
    demo.enabled = True
    demo.storage_root_dir = tmp_path / "data"
    demo.save()

    payload = json.loads(settings_path.read_text(encoding="utf-8"))
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
    demo = DemoSettings(path=settings_path)

    assert demo.storage_root_dir is None


def test_path_field_removes_key_after_save(tmp_path) -> None:
    settings_path = tmp_path / "settings.json"
    demo = DemoSettings(path=settings_path)
    demo.storage_root_dir = tmp_path / "data"
    demo.save()

    demo.storage_root_dir = None
    payload_before_save = json.loads(settings_path.read_text(encoding="utf-8"))
    assert payload_before_save["demo"]["storage"]["root_dir"] == str(tmp_path / "data")

    demo.save()

    payload_after_save = json.loads(settings_path.read_text(encoding="utf-8"))
    assert payload_after_save == {}
    assert demo.storage_root_dir is None


def test_path_field_rejects_blank_strings(tmp_path) -> None:
    demo = DemoSettings(path=tmp_path / "settings.json")

    try:
        demo.storage_root_dir = "  "
    except ValueError as exc:
        assert str(exc) == "demo.storage.root_dir must not be empty"
    else:
        raise AssertionError("blank path should fail")
