from __future__ import annotations

from modlink_plugin_scaffold.textual_app.services import build_spec, set_data_arrival, set_driver_kind, set_plugin_name, set_stream_field, validate_draft
from modlink_plugin_scaffold.textual_app.state import ScaffoldDraft


def test_set_plugin_name_updates_default_display_name_and_device_id() -> None:
    draft = ScaffoldDraft()

    set_plugin_name(draft, "Fancy Sensor")

    assert draft.display_name == "FancySensor"
    assert draft.device_id == "fancy_sensor.01"


def test_data_arrival_recommendation_respects_manual_override() -> None:
    draft = ScaffoldDraft()

    set_data_arrival(draft, "poll")
    assert draft.driver_kind == "loop"

    set_driver_kind(draft, "driver")
    set_data_arrival(draft, "push")

    assert draft.driver_kind == "driver"


def test_payload_defaults_flow_into_built_spec() -> None:
    draft = ScaffoldDraft()

    set_stream_field(draft, 0, "payload_type", "video")

    spec = build_spec("en", draft)
    stream = spec.streams[0]

    assert stream.payload_type == "video"
    assert stream.video_height == 480
    assert stream.video_width == 640
    assert stream.channel_names == ("red", "green", "blue")


def test_validate_draft_reports_blocking_errors() -> None:
    draft = ScaffoldDraft(providers_text="")

    validation = validate_draft("en", draft)

    assert validation.spec is None
    assert validation.can_generate is False
    assert validation.field_errors["providers"] == "Provide at least one provider token."
