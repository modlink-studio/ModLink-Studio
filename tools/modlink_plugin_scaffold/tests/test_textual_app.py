from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from textual.pilot import Pilot
from textual.widgets import Button

from modlink_plugin_scaffold.textual_app import ScaffoldTextualApp


def _run_app(
    scenario,
    *,
    language: str = "en",
    working_dir: Path | None = None,
) -> None:
    async def runner() -> None:
        app = ScaffoldTextualApp(language=language, working_dir=working_dir)
        async with app.run_test() as pilot:
            await pilot.pause()
            await scenario(app, pilot)

    asyncio.run(runner())


def _visual_text(app: ScaffoldTextualApp, selector: str) -> str:
    return str(app.query_one(selector).visual)


@pytest.mark.parametrize(
    ("language", "expected_button", "expected_summary"),
    [
        ("en", "Generate Scaffold", "Scaffold Summary"),
        ("zh", "生成脚手架", "脚手架摘要"),
    ],
)
def test_app_starts_in_supported_languages(language: str, expected_button: str, expected_summary: str) -> None:
    async def scenario(app: ScaffoldTextualApp, pilot: Pilot) -> None:
        del pilot
        assert str(app.query_one("#generate-button", Button).label) == expected_button
        assert expected_summary in _visual_text(app, "#preview-content")

    _run_app(scenario, language=language)


def test_plugin_name_updates_derived_fields_and_summary() -> None:
    async def scenario(app: ScaffoldTextualApp, pilot: Pilot) -> None:
        app.set_input_value("plugin-name-input", "Fancy Sensor")
        await pilot.pause()

        assert app.query_one("#display-name-input").value == "FancySensor"
        assert app.query_one("#device-id-input").value == "fancy_sensor.01"
        assert "FancySensor" in _visual_text(app, "#preview-content")
        assert "fancy_sensor.01" in _visual_text(app, "#preview-content")

    _run_app(scenario)


def test_stream_actions_and_selection_sync() -> None:
    async def scenario(app: ScaffoldTextualApp, pilot: Pilot) -> None:
        app.click_stream_action("add")
        await pilot.pause()
        app.click_stream_action("duplicate")
        await pilot.pause()
        app.click_stream_action("up")
        await pilot.pause()

        assert len(app.draft.streams) == 3
        assert app.draft.selected_stream_index == 1

        app.choose_stream(0)
        await pilot.pause()

        heading = _visual_text(app, "#stream-detail-heading")
        assert "#1" in heading

        app.click_stream_action("delete")
        await pilot.pause()

        assert len(app.draft.streams) == 2

    _run_app(scenario)


def test_payload_switch_updates_defaults_and_preview_tabs() -> None:
    async def scenario(app: ScaffoldTextualApp, pilot: Pilot) -> None:
        app.set_select_value("stream-payload-select", "video")
        await pilot.pause()

        assert app.draft.streams[0].payload_type == "video"
        assert app.query_one("#stream-video-height-input").value == "480"
        assert app.query_one("#row-stream-video-height").display is True
        assert app.query_one("#row-stream-channel-count").display is False

        app.activate_preview_tab("driver_py")
        await pilot.pause()

        assert '"""MyDevice driver implementation.' in _visual_text(app, "#preview-content")

    _run_app(scenario)


def test_invalid_input_disables_generate_and_shows_placeholder_preview() -> None:
    async def scenario(app: ScaffoldTextualApp, pilot: Pilot) -> None:
        app.set_input_value("providers-input", "")
        await pilot.pause()

        assert app.query_one("#generate-button", Button).disabled is True
        assert "Provide at least one provider token." in _visual_text(app, "#validation-banner")

        app.activate_preview_tab("pyproject")
        await pilot.pause()

        assert "Preview is unavailable until the current draft passes validation." in _visual_text(app, "#preview-content")

    _run_app(scenario)


def test_generate_creates_project_and_opens_completion_screen(tmp_path: Path) -> None:
    async def scenario(app: ScaffoldTextualApp, pilot: Pilot) -> None:
        app.action_generate()
        await pilot.pause()

        assert type(app.screen).__name__ == "CompletionScreen"
        assert (tmp_path / "my_device" / "pyproject.toml").exists()
        assert (tmp_path / "my_device" / "my_device" / "driver.py").exists()

    _run_app(scenario, working_dir=tmp_path)


def test_existing_project_prompts_before_overwrite(tmp_path: Path) -> None:
    async def scenario(app: ScaffoldTextualApp, pilot: Pilot) -> None:
        target = tmp_path / "my_device"
        target.mkdir()
        sentinel = target / "sentinel.txt"
        sentinel.write_text("keep", encoding="utf-8")

        app.action_generate()
        await pilot.pause()

        assert type(app.screen).__name__ == "ConfirmOverwriteScreen"

        await pilot.click("#cancel-overwrite")
        await pilot.pause()

        assert type(app.screen).__name__ == "Screen"
        assert sentinel.exists()

        app.action_generate()
        await pilot.pause()
        await pilot.click("#confirm-overwrite")
        await pilot.pause()

        assert type(app.screen).__name__ == "CompletionScreen"
        assert not sentinel.exists()
        assert (target / "my_device" / "driver.py").exists()

    _run_app(scenario, working_dir=tmp_path)
