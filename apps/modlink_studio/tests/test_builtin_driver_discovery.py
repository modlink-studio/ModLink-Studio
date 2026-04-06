from __future__ import annotations

from importlib.metadata import distribution


def test_modlink_studio_distribution_no_longer_exposes_builtin_driver_entry_points() -> None:
    driver_entry_points = {
        entry_point.name
        for entry_point in distribution("modlink-studio").entry_points
        if entry_point.group == "modlink.drivers"
    }

    assert driver_entry_points == set()


def test_modlink_studio_distribution_exposes_plugin_cli_script() -> None:
    console_scripts = {
        entry_point.name
        for entry_point in distribution("modlink-studio").entry_points
        if entry_point.group == "console_scripts"
    }

    assert "modlink-studio-plugin" in console_scripts
