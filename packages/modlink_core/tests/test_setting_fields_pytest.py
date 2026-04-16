from __future__ import annotations

from types import MappingProxyType

import pytest

from modlink_core.settings import (
    SettingItem,
    SettingsBool,
    SettingsGroup,
    SettingsInt,
    SettingsList,
    SettingsStore,
    SettingsStr,
)


def _build_demo_settings(path):
    settings = SettingsStore(path=path)
    settings.add(
        ui=SettingsGroup(
            labels=SettingsList(default=["alpha"]),
            preview=SettingsGroup(
                sample_rate=SettingsInt(default=48_000, min=8_000, max=192_000),
                enabled=SettingsBool(default=False),
                title=SettingsStr(default="Preview"),
            ),
        )
    )
    return settings


def test_declared_tree_exposes_nodes_and_items_with_value_reads(tmp_path) -> None:
    settings = _build_demo_settings(tmp_path / "settings.json")

    assert isinstance(settings.ui.preview.sample_rate, SettingItem)
    assert settings.ui.preview.sample_rate.path == "ui.preview.sample_rate"
    assert settings.ui.preview.sample_rate.value == 48_000
    assert settings.ui.preview.enabled.value is False
    assert settings.ui.preview.title.value == "Preview"


def test_list_values_are_frozen_and_do_not_share_input_storage(tmp_path) -> None:
    settings = _build_demo_settings(tmp_path / "settings.json")
    labels = ["left", {"name": "Fp1"}, {1, 2}]

    settings.ui.labels = labels
    labels[0] = "mutated"
    labels[1]["name"] = "Fp2"
    labels[2].add(3)

    frozen = settings.ui.labels.value

    assert frozen[0] == "left"
    assert isinstance(frozen, tuple)
    assert isinstance(frozen[1], MappingProxyType)
    assert frozen[1]["name"] == "Fp1"
    assert frozen[2] == frozenset({1, 2})


def test_attribute_assignment_routes_through_declared_item_validation(tmp_path) -> None:
    settings = _build_demo_settings(tmp_path / "settings.json")

    settings.ui.preview.sample_rate = 44_100

    assert settings.ui.preview.sample_rate.value == 44_100

    with pytest.raises(ValueError, match="min 8000"):
        settings.ui.preview.sample_rate = 1

    with pytest.raises(AttributeError, match="ui.preview is a group"):
        settings.ui.preview = 1

    with pytest.raises(AttributeError, match="ui.preview.unknown is not declared"):
        settings.ui.preview.unknown = 1


def test_add_merges_group_specs_and_rejects_conflicts(tmp_path) -> None:
    settings = SettingsStore(path=tmp_path / "settings.json")

    settings.add(ui=SettingsGroup(preview=SettingsGroup()))
    settings.ui.preview.add(sample_rate=SettingsInt(default=48_000))
    settings.add(ui=SettingsGroup(labels=SettingsList()))

    assert settings.ui.preview.sample_rate.value == 48_000
    assert settings.ui.labels.value == ()

    with pytest.raises(KeyError, match="duplicate key: ui.preview.sample_rate"):
        settings.ui.preview.add(sample_rate=SettingsInt(default=44_100))

    with pytest.raises(KeyError, match="duplicate key: ui.preview"):
        settings.add(ui=SettingsGroup(preview=SettingsInt(default=1)))

    with pytest.raises(KeyError, match="ui.preview.sample_rate already exists as a setting"):
        settings.add(
            ui=SettingsGroup(
                preview=SettingsGroup(
                    sample_rate=SettingsGroup(),
                )
            )
        )


def test_group_specs_are_declaration_only_objects(tmp_path) -> None:
    _ = tmp_path
    preview = SettingsGroup(sample_rate=SettingsInt(default=48_000))

    with pytest.raises(AttributeError):
        _ = preview.sample_rate

    with pytest.raises(AttributeError):
        preview.sample_rate = 44_100
