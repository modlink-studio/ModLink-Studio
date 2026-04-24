"""Validation logic for scaffold configuration."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .i18n import DATA_ARRIVAL_ORDER, DRIVER_KIND_ORDER, PAYLOAD_TYPE_ORDER, get_copy
from .models import (
    DataArrival,
    DriverKind,
    Draft,
    DriverSpec,
    PayloadType,
    StreamDraft,
    StreamSpec,
)
from .i18n import Language


DEVICE_ID_PATTERN = re.compile(r"^[a-z0-9_]+\.[0-9]{2,}$")


@dataclass
class ValidationResult:
    """Result of draft validation."""

    spec: DriverSpec | None
    field_errors: dict[str, str]
    recommended_driver_kind: DriverKind
    recommended_reason: str


def sanitize_identifier(value: str) -> str:
    """Sanitize a string to be a valid Python identifier."""
    normalized = (
        re.sub(r"[^\w\s-]", "", str(value))
        .replace("-", "_")
        .replace(" ", "_")
        .lower()
        .strip("_")
    )
    if not normalized:
        return ""
    if re.match(r"^\d", normalized):
        return f"plugin_{normalized}"
    return normalized


def normalize_token(value: str) -> str:
    """Normalize a token to lowercase snake_case."""
    return (
        str(value)
        .strip()
        .lower()
        .replace("-", "_")
        .replace(" ", "_")
        .replace("_+", "_")
        .strip("_")
    )


def to_pascal_case(value: str) -> str:
    """Convert a string to PascalCase."""
    parts = re.split(r"[_-]+", normalize_token(value))
    return "".join(f"{p[0].upper()}{p[1:]}" for p in parts if p)


def to_title_words(value: str) -> str:
    """Convert a string to Title Words."""
    parts = normalize_token(value).split("_")
    return " ".join(f"{p[0].upper()}{p[1:]}" for p in parts if p)


def make_device_id(plugin_name: str) -> str:
    """Generate a device ID from plugin name."""
    normalized = normalize_token(plugin_name)
    return f"{normalized}.01" if normalized else ""


def split_csv(value: str) -> list[str]:
    """Split a comma-separated string into unique items."""
    items = [item.strip() for item in str(value).split(",") if item.strip()]
    return list(dict.fromkeys(items))


def positive_int(value: str) -> int | None:
    """Parse a positive integer from a string."""
    try:
        parsed = int(str(value).strip())
        return parsed if parsed > 0 else None
    except ValueError:
        return None


def positive_float(value: str) -> float | None:
    """Parse a positive float from a string."""
    try:
        parsed = float(str(value).strip())
        return parsed if parsed > 0 and parsed != float("inf") else None
    except ValueError:
        return None


def recommended_driver_kind(data_arrival: DataArrival) -> DriverKind:
    """Get recommended driver kind for data arrival mode."""
    return "loop" if data_arrival == "poll" else "driver"


def driver_reason(language: Language, data_arrival: DataArrival, driver_kind: DriverKind) -> str:
    """Get reason text for driver kind selection."""
    copy = get_copy(language)
    if data_arrival == "push":
        key = "reason_push_driver" if driver_kind == "driver" else "reason_push_loop"
    elif data_arrival == "poll":
        key = "reason_poll_loop" if driver_kind == "loop" else "reason_poll_driver"
    else:
        key = "reason_unsure_driver" if driver_kind == "driver" else "reason_unsure_loop"
    return copy.get(key, "") if isinstance(copy.get(key), str) else ""


def apply_plugin_name_defaults(draft: Draft, value: str) -> Draft:
    """Apply plugin name and auto-fill related fields."""
    previous_name = draft.plugin_name
    previous_display = to_pascal_case(sanitize_identifier(previous_name) or previous_name)
    previous_device_id = make_device_id(previous_name)
    normalized = sanitize_identifier(value)

    new_display = draft.display_name
    if not draft.display_name.strip() or draft.display_name == previous_display:
        new_display = to_pascal_case(normalized) if normalized else ""

    new_device_id = draft.device_id
    if not draft.device_id.strip() or draft.device_id == previous_device_id:
        new_device_id = make_device_id(value)

    return Draft(
        plugin_name=value,
        display_name=new_display,
        device_id=new_device_id,
        providers_text=draft.providers_text,
        data_arrival=draft.data_arrival,
        driver_kind=draft.driver_kind,
        dependencies_text=draft.dependencies_text,
        streams=draft.streams,
    )


def apply_data_arrival_defaults(draft: Draft, value: DataArrival) -> Draft:
    """Apply data arrival and update driver kind if using default."""
    if value not in DATA_ARRIVAL_ORDER:
        return draft

    previous_recommended = recommended_driver_kind(draft.data_arrival)
    new_driver_kind = draft.driver_kind
    if draft.driver_kind == previous_recommended:
        new_driver_kind = recommended_driver_kind(value)

    return Draft(
        plugin_name=draft.plugin_name,
        display_name=draft.display_name,
        device_id=draft.device_id,
        providers_text=draft.providers_text,
        data_arrival=value,
        driver_kind=new_driver_kind,
        dependencies_text=draft.dependencies_text,
        streams=draft.streams,
    )


def apply_payload_defaults(stream: StreamDraft, payload_type: PayloadType) -> StreamDraft:
    """Apply default values based on payload type."""
    defaults: dict[PayloadType, dict[str, str]] = {
        "signal": {
            "sample_rate_hz": "250",
            "chunk_size": "25",
            "channel_count": "2",
            "channel_names": "ch1, ch2",
        },
        "raster": {
            "sample_rate_hz": "10",
            "chunk_size": "1",
            "channel_count": "1",
            "channel_names": "intensity",
            "raster_length": "128",
        },
        "field": {
            "sample_rate_hz": "10",
            "chunk_size": "1",
            "channel_count": "1",
            "channel_names": "intensity",
            "field_height": "48",
            "field_width": "48",
        },
        "video": {
            "sample_rate_hz": "30",
            "chunk_size": "1",
            "channel_count": "3",
            "channel_names": "red, green, blue",
            "video_height": "480",
            "video_width": "640",
        },
    }

    base = stream.model_dump()
    # Clear unit for video
    if payload_type == "video":
        base["unit"] = ""

    for key, val in defaults.get(payload_type, {}).items():
        base[key] = val

    base["payload_type"] = payload_type
    return StreamDraft(**base)


def validate_stream(
    language: Language,
    stream: StreamDraft,
    index: int,
    field_errors: dict[str, str],
) -> StreamSpec | None:
    """Validate a single stream and return spec or None on error."""
    copy = get_copy(language)
    prefix = f"streams.{index}"
    stream_key = normalize_token(stream.stream_key)

    if not stream_key:
        field_errors[f"{prefix}.streamKey"] = copy.get("stream_key_error", "") if isinstance(copy.get("stream_key_error"), str) else ""

    if stream.payload_type not in PAYLOAD_TYPE_ORDER:
        field_errors[f"{prefix}.payloadType"] = copy.get("validation_blocked", "") if isinstance(copy.get("validation_blocked"), str) else ""
        return None

    sample_rate_hz = positive_float(stream.sample_rate_hz)
    if sample_rate_hz is None:
        field_errors[f"{prefix}.sampleRateHz"] = copy.get("positive_float_error", "") if isinstance(copy.get("positive_float_error"), str) else ""

    chunk_size = positive_int(stream.chunk_size)
    if chunk_size is None:
        field_errors[f"{prefix}.chunkSize"] = copy.get("positive_int_error", "") if isinstance(copy.get("positive_int_error"), str) else ""

    channel_names = split_csv(stream.channel_names)
    if not channel_names:
        field_errors[f"{prefix}.channelNames"] = copy.get("channel_names_error", "") if isinstance(copy.get("channel_names_error"), str) else ""

    channel_count = positive_int(stream.channel_count)
    if stream.payload_type == "signal":
        if channel_count is None:
            field_errors[f"{prefix}.channelCount"] = copy.get("positive_int_error", "") if isinstance(copy.get("positive_int_error"), str) else ""
        elif channel_names and len(channel_names) != channel_count:
            field_errors[f"{prefix}.channelNames"] = copy.get("channel_names_count_error", "") if isinstance(copy.get("channel_names_count_error"), str) else ""

    raster_length = positive_int(stream.raster_length) if stream.payload_type == "raster" else None
    if stream.payload_type == "raster" and raster_length is None:
        field_errors[f"{prefix}.rasterLength"] = copy.get("positive_int_error", "") if isinstance(copy.get("positive_int_error"), str) else ""

    field_height = positive_int(stream.field_height) if stream.payload_type == "field" else None
    field_width = positive_int(stream.field_width) if stream.payload_type == "field" else None
    if stream.payload_type == "field":
        if field_height is None:
            field_errors[f"{prefix}.fieldHeight"] = copy.get("positive_int_error", "") if isinstance(copy.get("positive_int_error"), str) else ""
        if field_width is None:
            field_errors[f"{prefix}.fieldWidth"] = copy.get("positive_int_error", "") if isinstance(copy.get("positive_int_error"), str) else ""

    video_height = positive_int(stream.video_height) if stream.payload_type == "video" else None
    video_width = positive_int(stream.video_width) if stream.payload_type == "video" else None
    if stream.payload_type == "video":
        if video_height is None:
            field_errors[f"{prefix}.videoHeight"] = copy.get("positive_int_error", "") if isinstance(copy.get("positive_int_error"), str) else ""
        if video_width is None:
            field_errors[f"{prefix}.videoWidth"] = copy.get("positive_int_error", "") if isinstance(copy.get("positive_int_error"), str) else ""

    # Check if any errors for this stream
    if any(key.startswith(f"{prefix}.") for key in field_errors):
        return None

    default_stream_name = copy.get("default_stream_name", "Stream")
    default_name = f"{to_title_words(stream_key)} {default_stream_name}" if isinstance(default_stream_name, str) else f"{to_title_words(stream_key)} Stream"

    return StreamSpec(
        stream_key=stream_key,
        display_name=stream.display_name.strip() or default_name,
        payload_type=stream.payload_type,
        sample_rate_hz=sample_rate_hz or 1,
        chunk_size=chunk_size or 1,
        channel_names=channel_names,
        unit=stream.unit.strip() or None,
        raster_length=raster_length,
        field_height=field_height,
        field_width=field_width,
        video_height=video_height,
        video_width=video_width,
    )


def validate_draft(language: Language, draft: Draft) -> ValidationResult:
    """Validate the entire draft and return result."""
    copy = get_copy(language)
    field_errors: dict[str, str] = {}

    # Validate plugin name
    plugin_name = sanitize_identifier(draft.plugin_name)
    if not plugin_name:
        field_errors["pluginName"] = copy.get("plugin_name_error", "") if isinstance(copy.get("plugin_name_error"), str) else ""

    # Validate device ID
    device_id = (draft.device_id.strip() or make_device_id(draft.plugin_name)).strip().lower().replace("-", "_")
    if not DEVICE_ID_PATTERN.match(device_id):
        field_errors["deviceId"] = copy.get("device_id_error", "") if isinstance(copy.get("device_id_error"), str) else ""

    # Validate providers
    providers = [normalize_token(p) for p in split_csv(draft.providers_text) if normalize_token(p)]
    if not providers:
        field_errors["providersText"] = copy.get("providers_error", "") if isinstance(copy.get("providers_error"), str) else ""

    # Validate streams exist
    if not draft.streams:
        field_errors["streams"] = copy.get("streams_required_error", "") if isinstance(copy.get("streams_required_error"), str) else ""

    # Validate each stream
    stream_specs = [
        spec for spec in (
            validate_stream(language, stream, i, field_errors)
            for i, stream in enumerate(draft.streams)
        ) if spec is not None
    ]

    # Build spec if no errors
    spec: DriverSpec | None = None
    if not field_errors:
        extra_deps = split_csv(draft.dependencies_text)
        all_deps = list(dict.fromkeys(["modlink-sdk", "numpy>=2.3.3"] + extra_deps))

        driver_kind = draft.driver_kind if draft.driver_kind in DRIVER_KIND_ORDER else "driver"

        spec = DriverSpec(
            plugin_name=plugin_name,
            project_name=plugin_name.replace("_", "-"),
            class_name=to_pascal_case(plugin_name),
            display_name=draft.display_name.strip() or to_pascal_case(plugin_name),
            device_id=device_id,
            providers=providers,
            driver_kind=driver_kind,
            driver_reason=driver_reason(language, draft.data_arrival, driver_kind),
            data_arrival=draft.data_arrival,
            dependencies=all_deps,
            streams=stream_specs,
        )

    return ValidationResult(
        spec=spec,
        field_errors=field_errors,
        recommended_driver_kind=recommended_driver_kind(draft.data_arrival),
        recommended_reason=driver_reason(language, draft.data_arrival, recommended_driver_kind(draft.data_arrival)),
    )