from __future__ import annotations

from pathlib import Path

import pytest

from modlink_plugin_scaffold.core.context import create_project_context
from modlink_plugin_scaffold.core.generator import create_plugin_scaffold
from modlink_plugin_scaffold.core.spec import DriverSpec, StreamSpec


def _make_spec() -> DriverSpec:
    return DriverSpec(
        plugin_name="test_driver",
        display_name="TestDriver",
        device_id="test_driver.01",
        providers=("serial",),
        driver_kind="driver",
        driver_reason="Testing scaffold generation.",
        data_arrival="push",
        streams=(
            StreamSpec(
                modality="imu",
                payload_type="signal",
                display_name="IMU Stream",
                sample_rate_hz=200.0,
                chunk_size=20,
                channel_names=("ax", "ay", "az"),
                unit="g",
            ),
        ),
    )


def test_create_plugin_scaffold_requires_overwrite_for_existing_dir(tmp_path: Path) -> None:
    context = create_project_context(tmp_path)
    spec = _make_spec()

    paths = create_plugin_scaffold(context, spec)

    assert paths.project_dir.exists()
    assert paths.driver_path.exists()
    assert paths.pyproject_path.exists()

    with pytest.raises(FileExistsError):
        create_plugin_scaffold(context, spec)


def test_create_plugin_scaffold_overwrite_replaces_existing_output(tmp_path: Path) -> None:
    context = create_project_context(tmp_path)
    spec = _make_spec()

    create_plugin_scaffold(context, spec)
    sentinel = tmp_path / "test_driver" / "sentinel.txt"
    sentinel.write_text("old", encoding="utf-8")

    paths = create_plugin_scaffold(context, spec, overwrite=True)

    assert not sentinel.exists()
    assert paths.driver_path.exists()
    assert "TestDriver" in paths.driver_path.read_text(encoding="utf-8")
