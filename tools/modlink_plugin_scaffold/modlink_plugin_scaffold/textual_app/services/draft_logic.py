"""Draft mutation and validation helpers for the Textual scaffold app."""

from __future__ import annotations

from dataclasses import dataclass, replace

from ...core.spec import (
    DriverKind,
    DriverSpec,
    PayloadType,
    StreamSpec,
    is_valid_device_id,
    make_device_id,
    normalize_token,
    sanitize_identifier,
    to_pascal_case,
    unique_strings,
)
from ...i18n import DATA_ARRIVAL_CHOICES, PAYLOAD_CHOICES, Language, t
from ..state import PreviewTab, ScaffoldDraft, StreamDraft, make_default_stream

STREAM_FIELD_VISIBILITY: dict[PayloadType, tuple[str, ...]] = {
    "signal": ("channel_count", "channel_names", "unit"),
    "raster": ("raster_length", "channel_names", "unit"),
    "field": ("field_height", "field_width", "channel_names", "unit"),
    "video": ("video_height", "video_width", "channel_names"),
}


@dataclass(frozen=True, slots=True)
class DraftValidation:
    spec: DriverSpec | None
    field_errors: dict[str, str]
    recommended_driver_kind: DriverKind
    recommended_reason: str

    @property
    def can_generate(self) -> bool:
        return self.spec is not None

    @property
    def first_error(self) -> str:
        return next(iter(self.field_errors.values()), "")


def set_plugin_name(draft: ScaffoldDraft, value: str) -> None:
    previous_plugin_name = draft.plugin_name
    previous_default_display = to_pascal_case(sanitize_identifier(previous_plugin_name) or previous_plugin_name)
    previous_default_device = _default_device_id(previous_plugin_name)
    draft.plugin_name = value
    normalized = sanitize_identifier(value)
    if not draft.display_name.strip() or draft.display_name == previous_default_display:
        draft.display_name = to_pascal_case(normalized) if normalized else ""
    if not draft.device_id.strip() or draft.device_id == previous_default_device:
        draft.device_id = _default_device_id(value)


def set_display_name(draft: ScaffoldDraft, value: str) -> None:
    draft.display_name = value


def set_device_id(draft: ScaffoldDraft, value: str) -> None:
    draft.device_id = value


def set_providers_text(draft: ScaffoldDraft, value: str) -> None:
    draft.providers_text = value


def set_data_arrival(draft: ScaffoldDraft, value: str) -> None:
    if value not in {choice.key for choice in DATA_ARRIVAL_CHOICES}:
        return
    previous_recommended = recommended_driver_kind(draft.data_arrival)
    draft.data_arrival = value  # type: ignore[assignment]
    if draft.driver_kind == previous_recommended:
        draft.driver_kind = recommended_driver_kind(draft.data_arrival)


def set_driver_kind(draft: ScaffoldDraft, value: str) -> None:
    if value in {"driver", "loop"}:
        draft.driver_kind = value  # type: ignore[assignment]


def set_dependencies_text(draft: ScaffoldDraft, value: str) -> None:
    draft.dependencies_text = value


def set_preview_tab(draft: ScaffoldDraft, value: PreviewTab) -> None:
    draft.preview_tab = value


def add_stream(draft: ScaffoldDraft) -> None:
    draft.streams.append(make_default_stream(len(draft.streams)))
    draft.selected_stream_index = len(draft.streams) - 1


def duplicate_stream(draft: ScaffoldDraft) -> None:
    stream = draft.streams[draft.selected_stream_index]
    duplicated = replace(stream)
    draft.streams.insert(draft.selected_stream_index + 1, duplicated)
    draft.selected_stream_index += 1


def delete_stream(draft: ScaffoldDraft) -> None:
    if len(draft.streams) <= 1:
        draft.streams[0] = make_default_stream(0)
        draft.selected_stream_index = 0
        return
    draft.streams.pop(draft.selected_stream_index)
    draft.selected_stream_index = min(draft.selected_stream_index, len(draft.streams) - 1)


def move_stream_up(draft: ScaffoldDraft) -> None:
    index = draft.selected_stream_index
    if index <= 0:
        return
    draft.streams[index - 1], draft.streams[index] = draft.streams[index], draft.streams[index - 1]
    draft.selected_stream_index -= 1


def move_stream_down(draft: ScaffoldDraft) -> None:
    index = draft.selected_stream_index
    if index >= len(draft.streams) - 1:
        return
    draft.streams[index + 1], draft.streams[index] = draft.streams[index], draft.streams[index + 1]
    draft.selected_stream_index += 1


def select_stream(draft: ScaffoldDraft, index: int) -> None:
    if 0 <= index < len(draft.streams):
        draft.selected_stream_index = index


def set_stream_field(draft: ScaffoldDraft, stream_index: int, field_name: str, value: str) -> None:
    stream = draft.streams[stream_index]
    if field_name == "payload_type":
        if value in {choice.key for choice in PAYLOAD_CHOICES}:
            _apply_payload_defaults(stream, value)
        return

    setattr(stream, field_name, value)

    if field_name == "channel_count":
        parsed = _parse_positive_int(value)
        if parsed is not None:
            stream.channel_names = ", ".join(f"ch{index + 1}" for index in range(parsed))


def visible_stream_fields(payload_type: PayloadType) -> tuple[str, ...]:
    return STREAM_FIELD_VISIBILITY[payload_type]


def recommended_driver_kind(data_arrival: str) -> DriverKind:
    if data_arrival == "poll":
        return "loop"
    return "driver"


def driver_selection_reason(language: Language, data_arrival: str, driver_kind: str) -> str:
    if data_arrival == "push":
        return t(language, "reason_push_driver") if driver_kind == "driver" else t(language, "reason_push_loop")
    if data_arrival == "poll":
        return t(language, "reason_poll_loop") if driver_kind == "loop" else t(language, "reason_poll_driver")
    return t(language, "reason_unsure_driver") if driver_kind == "driver" else t(language, "reason_unsure_loop")


def validate_draft(language: Language, draft: ScaffoldDraft) -> DraftValidation:
    errors: dict[str, str] = {}

    plugin_name = sanitize_identifier(draft.plugin_name)
    if not plugin_name:
        errors["plugin_name"] = t(language, "plugin_name_error")

    resolved_device_id = (draft.device_id.strip() or _default_device_id(draft.plugin_name)).strip()
    if not resolved_device_id or not is_valid_device_id(resolved_device_id):
        errors["device_id"] = t(language, "device_id_error")

    providers = _parse_provider_tokens(draft.providers_text)
    if not providers:
        errors["providers"] = t(language, "providers_error")

    if draft.data_arrival not in {choice.key for choice in DATA_ARRIVAL_CHOICES}:
        errors["data_arrival"] = t(language, "choice_error")
    if draft.driver_kind not in {"driver", "loop"}:
        errors["driver_kind"] = t(language, "choice_error")
    if not draft.streams:
        errors["streams"] = t(language, "streams_required_error")

    stream_specs: list[StreamSpec] = []
    for index, stream in enumerate(draft.streams):
        spec = _validate_stream(language, index, stream, errors)
        if spec is not None:
            stream_specs.append(spec)

    spec: DriverSpec | None = None
    if not errors:
        try:
            spec = DriverSpec(
                plugin_name=draft.plugin_name,
                display_name=draft.display_name.strip() or to_pascal_case(plugin_name),
                device_id=resolved_device_id,
                providers=providers,
                driver_kind=draft.driver_kind,
                driver_reason=driver_selection_reason(language, draft.data_arrival, draft.driver_kind),
                data_arrival=draft.data_arrival,
                streams=tuple(stream_specs),
                dependencies=_parse_dependencies(draft.dependencies_text),
            )
        except ValueError as exc:
            errors["__global__"] = str(exc)

    return DraftValidation(
        spec=spec,
        field_errors=errors,
        recommended_driver_kind=recommended_driver_kind(draft.data_arrival),
        recommended_reason=driver_selection_reason(language, draft.data_arrival, recommended_driver_kind(draft.data_arrival)),
    )


def build_spec(language: Language, draft: ScaffoldDraft) -> DriverSpec:
    validation = validate_draft(language, draft)
    if validation.spec is None:
        raise ValueError(validation.first_error or t(language, "validation_blocked"))
    return validation.spec


def _validate_stream(
    language: Language,
    index: int,
    stream: StreamDraft,
    errors: dict[str, str],
) -> StreamSpec | None:
    field_prefix = f"stream.{index}"
    modality = normalize_token(stream.modality)
    if not modality:
        errors[f"{field_prefix}.modality"] = t(language, "modality_error")

    if stream.payload_type not in {choice.key for choice in PAYLOAD_CHOICES}:
        errors[f"{field_prefix}.payload_type"] = t(language, "choice_error")
        return None

    sample_rate_hz = _parse_positive_float(stream.sample_rate_hz)
    if sample_rate_hz is None:
        errors[f"{field_prefix}.sample_rate_hz"] = t(language, "positive_float_error")

    chunk_size = _parse_positive_int(stream.chunk_size)
    if chunk_size is None:
        errors[f"{field_prefix}.chunk_size"] = t(language, "positive_int_error")

    channel_names = _split_csv_values(stream.channel_names)
    if not channel_names:
        errors[f"{field_prefix}.channel_names"] = t(language, "channel_names_error")

    channel_count_value = _parse_positive_int(stream.channel_count)
    if stream.payload_type == "signal":
        if channel_count_value is None:
            errors[f"{field_prefix}.channel_count"] = t(language, "positive_int_error")
        elif channel_names and len(channel_names) != channel_count_value:
            errors[f"{field_prefix}.channel_names"] = t(language, "signal_channel_names_count_error")

    raster_length = _parse_positive_int(stream.raster_length) if stream.payload_type == "raster" else None
    if stream.payload_type == "raster" and raster_length is None:
        errors[f"{field_prefix}.raster_length"] = t(language, "positive_int_error")

    field_height = _parse_positive_int(stream.field_height) if stream.payload_type == "field" else None
    field_width = _parse_positive_int(stream.field_width) if stream.payload_type == "field" else None
    if stream.payload_type == "field":
        if field_height is None:
            errors[f"{field_prefix}.field_height"] = t(language, "positive_int_error")
        if field_width is None:
            errors[f"{field_prefix}.field_width"] = t(language, "positive_int_error")

    video_height = _parse_positive_int(stream.video_height) if stream.payload_type == "video" else None
    video_width = _parse_positive_int(stream.video_width) if stream.payload_type == "video" else None
    if stream.payload_type == "video":
        if video_height is None:
            errors[f"{field_prefix}.video_height"] = t(language, "positive_int_error")
        if video_width is None:
            errors[f"{field_prefix}.video_width"] = t(language, "positive_int_error")

    if any(key.startswith(field_prefix) for key in errors):
        return None

    return StreamSpec(
        modality=modality,
        payload_type=stream.payload_type,
        display_name=stream.display_name.strip(),
        sample_rate_hz=sample_rate_hz or 1.0,
        chunk_size=chunk_size or 1,
        channel_names=channel_names,
        unit=stream.unit.strip() or None,
        raster_length=raster_length,
        field_height=field_height,
        field_width=field_width,
        video_height=video_height,
        video_width=video_width,
    )


def _apply_payload_defaults(stream: StreamDraft, payload_type: str) -> None:
    stream.payload_type = payload_type  # type: ignore[assignment]
    if payload_type == "signal":
        stream.sample_rate_hz = "250"
        stream.chunk_size = "25"
        stream.channel_count = "2"
        stream.channel_names = "ch1, ch2"
        stream.unit = stream.unit or ""
        return
    if payload_type == "raster":
        stream.sample_rate_hz = "10"
        stream.chunk_size = "1"
        stream.channel_count = "1"
        stream.channel_names = "intensity"
        stream.raster_length = "128"
        stream.unit = stream.unit or ""
        return
    if payload_type == "field":
        stream.sample_rate_hz = "10"
        stream.chunk_size = "1"
        stream.channel_count = "1"
        stream.channel_names = "intensity"
        stream.field_height = "48"
        stream.field_width = "48"
        stream.unit = stream.unit or ""
        return
    stream.sample_rate_hz = "30"
    stream.chunk_size = "1"
    stream.channel_count = "3"
    stream.channel_names = "red, green, blue"
    stream.video_height = "480"
    stream.video_width = "640"
    stream.unit = ""


def _parse_positive_int(value: str) -> int | None:
    try:
        parsed = int(str(value).strip())
    except ValueError:
        return None
    return parsed if parsed > 0 else None


def _parse_positive_float(value: str) -> float | None:
    try:
        parsed = float(str(value).strip())
    except ValueError:
        return None
    return parsed if parsed > 0 else None


def _parse_provider_tokens(value: str) -> tuple[str, ...]:
    providers = [
        normalize_token(item)
        for item in str(value).split(",")
    ]
    return tuple(token for token in unique_strings(providers) if token)


def _parse_dependencies(value: str) -> tuple[str, ...]:
    return unique_strings([item.strip() for item in str(value).split(",") if item.strip()])


def _split_csv_values(value: str) -> tuple[str, ...]:
    return unique_strings([item.strip() for item in str(value).split(",") if item.strip()])


def _default_device_id(plugin_name: str) -> str:
    normalized = sanitize_identifier(plugin_name)
    if not normalized:
        return ""
    return make_device_id(normalized)
