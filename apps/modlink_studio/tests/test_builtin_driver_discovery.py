from __future__ import annotations

from importlib.metadata import entry_points

from modlink_sdk import Driver


def test_builtin_official_driver_entry_points_load_without_optional_dependencies() -> None:
    expected = {
        "host-camera",
        "host-microphone",
        "openbci-ganglion",
    }
    driver_entry_points = {
        entry_point.name: entry_point
        for entry_point in entry_points(group="modlink.drivers")
        if entry_point.name in expected
    }

    assert set(driver_entry_points) == expected

    for entry_point in driver_entry_points.values():
        factory = entry_point.load()
        driver = factory()
        assert isinstance(driver, Driver)
