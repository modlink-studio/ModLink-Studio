from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal, TypeAlias

PreviewPayloadType: TypeAlias = Literal["signal", "raster", "field", "video"]


SignalFilterFamily: TypeAlias = Literal["butterworth", "chebyshev1", "bessel"]
SignalFilterMode: TypeAlias = Literal[
    "none",
    "low_pass",
    "high_pass",
    "band_pass",
    "band_stop",
]
SignalLayoutMode: TypeAlias = Literal["stacked", "expanded"]
ValueRangeMode: TypeAlias = Literal["auto", "zero_to_one", "zero_to_255", "manual"]
SignalYAxisRangeMode: TypeAlias = Literal["auto", "manual"]
InterpolationMode: TypeAlias = Literal["nearest", "bilinear", "bicubic"]
TransformMode: TypeAlias = Literal[
    "none",
    "flip_horizontal",
    "flip_vertical",
    "rotate_90",
    "rotate_180",
    "rotate_270",
]
VideoColorFormat: TypeAlias = Literal["rgb", "bgr", "gray", "yuv"]
VideoScaleMode: TypeAlias = Literal["fit", "fill"]
VideoAspectMode: TypeAlias = Literal["keep", "stretch"]


@dataclass(slots=True)
class SignalFilterSettings:
    family: SignalFilterFamily = "butterworth"
    mode: SignalFilterMode = "none"
    order: int = 4
    low_cutoff_hz: float = 1.0
    high_cutoff_hz: float = 40.0
    notch_enabled: bool = False
    notch_frequencies_hz: tuple[float, ...] = ()
    notch_q: float = 30.0
    chebyshev1_ripple_db: float = 1.0


@dataclass(slots=True)
class SignalPreviewSettings:
    window_seconds: int = 8
    antialias_enabled: bool = True
    layout_mode: SignalLayoutMode = "expanded"
    visible_channel_indices: tuple[int, ...] = ()
    y_range_mode: SignalYAxisRangeMode = "auto"
    manual_y_min: float = -1.0
    manual_y_max: float = 1.0
    filter: SignalFilterSettings = field(default_factory=SignalFilterSettings)


@dataclass(slots=True)
class RasterPreviewSettings:
    window_seconds: int = 8
    colormap: str = "gray"
    value_range_mode: ValueRangeMode = "auto"
    manual_min: float = 0.0
    manual_max: float = 1.0
    interpolation: InterpolationMode = "nearest"
    transform: TransformMode = "none"


@dataclass(slots=True)
class FieldPreviewSettings:
    colormap: str = "gray"
    value_range_mode: ValueRangeMode = "auto"
    manual_min: float = 0.0
    manual_max: float = 1.0
    interpolation: InterpolationMode = "nearest"
    transform: TransformMode = "none"


@dataclass(slots=True)
class VideoPreviewSettings:
    color_format: VideoColorFormat = "rgb"
    scale_mode: VideoScaleMode = "fit"
    aspect_mode: VideoAspectMode = "keep"
    transform: TransformMode = "none"


PreviewSettings: TypeAlias = (
    SignalPreviewSettings | RasterPreviewSettings | FieldPreviewSettings | VideoPreviewSettings
)


def default_preview_settings(payload_type: PreviewPayloadType) -> PreviewSettings:
    if payload_type == "signal":
        return SignalPreviewSettings()
    if payload_type == "raster":
        return RasterPreviewSettings()
    if payload_type == "field":
        return FieldPreviewSettings()
    if payload_type == "video":
        return VideoPreviewSettings()
    raise ValueError(f"unsupported payload_type: {payload_type}")


def serialize_preview_settings(settings: PreviewSettings) -> dict[str, Any]:
    payload = asdict(settings)
    if isinstance(settings, SignalPreviewSettings):
        visible_channel_indices = payload.get("visible_channel_indices", [])
        if isinstance(visible_channel_indices, tuple):
            payload["visible_channel_indices"] = list(visible_channel_indices)
        filter_payload = payload.get("filter", {})
        if isinstance(filter_payload, dict):
            frequencies = filter_payload.get("notch_frequencies_hz", [])
            if isinstance(frequencies, (list, tuple)):
                filter_payload["notch_frequencies_hz"] = list(frequencies)
            payload["filter"] = filter_payload
    return payload


def deserialize_preview_settings(
    payload_type: PreviewPayloadType,
    payload: object,
) -> PreviewSettings:
    if not isinstance(payload, dict):
        return default_preview_settings(payload_type)

    if payload_type == "signal":
        filter_payload = payload.get("filter")
        if not isinstance(filter_payload, dict):
            filter_payload = {}
        notch_values = filter_payload.get("notch_frequencies_hz", [])
        notch_tuple = _coerce_float_tuple(notch_values)
        filter_settings = SignalFilterSettings(
            family=_coerce_literal(
                filter_payload.get("family"),
                ("butterworth", "chebyshev1", "bessel"),
                "butterworth",
            ),
            mode=_coerce_literal(
                filter_payload.get("mode"),
                ("none", "low_pass", "high_pass", "band_pass", "band_stop"),
                "none",
            ),
            order=_coerce_int(filter_payload.get("order"), 4),
            low_cutoff_hz=_coerce_float(filter_payload.get("low_cutoff_hz"), 1.0),
            high_cutoff_hz=_coerce_float(filter_payload.get("high_cutoff_hz"), 40.0),
            notch_enabled=bool(filter_payload.get("notch_enabled", False)),
            notch_frequencies_hz=notch_tuple,
            notch_q=_coerce_float(filter_payload.get("notch_q"), 30.0),
            chebyshev1_ripple_db=_coerce_float(
                filter_payload.get("chebyshev1_ripple_db"),
                1.0,
            ),
        )
        return SignalPreviewSettings(
            window_seconds=_coerce_int(payload.get("window_seconds"), 8),
            antialias_enabled=bool(payload.get("antialias_enabled", True)),
            layout_mode=_coerce_literal(
                payload.get("layout_mode"),
                ("stacked", "expanded"),
                "expanded",
            ),
            visible_channel_indices=_coerce_int_tuple(
                payload.get("visible_channel_indices"),
            ),
            y_range_mode=_coerce_literal(
                payload.get("y_range_mode"),
                ("auto", "manual"),
                "auto",
            ),
            manual_y_min=_coerce_float(payload.get("manual_y_min"), -1.0),
            manual_y_max=_coerce_float(payload.get("manual_y_max"), 1.0),
            filter=filter_settings,
        )

    if payload_type == "raster":
        return RasterPreviewSettings(
            window_seconds=_coerce_int(payload.get("window_seconds"), 8),
            colormap=_coerce_str(payload.get("colormap"), "gray"),
            value_range_mode=_coerce_literal(
                payload.get("value_range_mode"),
                ("auto", "zero_to_one", "zero_to_255", "manual"),
                "auto",
            ),
            manual_min=_coerce_float(payload.get("manual_min"), 0.0),
            manual_max=_coerce_float(payload.get("manual_max"), 1.0),
            interpolation=_coerce_literal(
                payload.get("interpolation"),
                ("nearest", "bilinear", "bicubic"),
                "nearest",
            ),
            transform=_coerce_literal(
                payload.get("transform"),
                (
                    "none",
                    "flip_horizontal",
                    "flip_vertical",
                    "rotate_90",
                    "rotate_180",
                    "rotate_270",
                ),
                "none",
            ),
        )

    if payload_type == "field":
        return FieldPreviewSettings(
            colormap=_coerce_str(payload.get("colormap"), "gray"),
            value_range_mode=_coerce_literal(
                payload.get("value_range_mode"),
                ("auto", "zero_to_one", "zero_to_255", "manual"),
                "auto",
            ),
            manual_min=_coerce_float(payload.get("manual_min"), 0.0),
            manual_max=_coerce_float(payload.get("manual_max"), 1.0),
            interpolation=_coerce_literal(
                payload.get("interpolation"),
                ("nearest", "bilinear", "bicubic"),
                "nearest",
            ),
            transform=_coerce_literal(
                payload.get("transform"),
                (
                    "none",
                    "flip_horizontal",
                    "flip_vertical",
                    "rotate_90",
                    "rotate_180",
                    "rotate_270",
                ),
                "none",
            ),
        )

    if payload_type == "video":
        return VideoPreviewSettings(
            color_format=_coerce_literal(
                payload.get("color_format"),
                ("rgb", "bgr", "gray", "yuv"),
                "rgb",
            ),
            scale_mode=_coerce_literal(
                payload.get("scale_mode"),
                ("fit", "fill"),
                "fit",
            ),
            aspect_mode=_coerce_literal(
                payload.get("aspect_mode"),
                ("keep", "stretch"),
                "keep",
            ),
            transform=_coerce_literal(
                payload.get("transform"),
                (
                    "none",
                    "flip_horizontal",
                    "flip_vertical",
                    "rotate_90",
                    "rotate_180",
                    "rotate_270",
                ),
                "none",
            ),
        )

    raise ValueError(f"unsupported payload_type: {payload_type}")


def normalize_preview_settings(
    payload_type: PreviewPayloadType,
    settings: PreviewSettings,
    nominal_sample_rate_hz: float,
    channel_names: tuple[str, ...] = (),
) -> PreviewSettings:
    if payload_type == "signal":
        assert isinstance(settings, SignalPreviewSettings)
        return _normalize_signal_settings(
            settings,
            nominal_sample_rate_hz,
            channel_names,
        )
    if payload_type == "raster":
        assert isinstance(settings, RasterPreviewSettings)
        return _normalize_raster_settings(settings)
    if payload_type == "field":
        assert isinstance(settings, FieldPreviewSettings)
        return _normalize_field_settings(settings)
    if payload_type == "video":
        assert isinstance(settings, VideoPreviewSettings)
        return _normalize_video_settings(settings)
    raise ValueError(f"unsupported payload_type: {payload_type}")


def _normalize_signal_settings(
    settings: SignalPreviewSettings,
    nominal_sample_rate_hz: float,
    channel_names: tuple[str, ...],
) -> SignalPreviewSettings:
    nyquist = max(float(nominal_sample_rate_hz or 1.0) / 2.0, 1.0)
    channel_count = max(len(channel_names), 0)
    window_seconds = max(1, int(settings.window_seconds))
    filter_settings = settings.filter

    order = min(max(int(filter_settings.order), 1), 12)
    low_cutoff = max(0.001, float(filter_settings.low_cutoff_hz))
    high_cutoff = max(0.001, float(filter_settings.high_cutoff_hz))
    max_cutoff = max(0.001, nyquist - 1e-6)
    low_cutoff = min(low_cutoff, max_cutoff)
    high_cutoff = min(high_cutoff, max_cutoff)
    if low_cutoff > high_cutoff:
        low_cutoff, high_cutoff = high_cutoff, low_cutoff

    if filter_settings.mode in {"band_pass", "band_stop"} and low_cutoff >= high_cutoff:
        low_cutoff = max(0.001, min(low_cutoff, max_cutoff * 0.5))
        high_cutoff = min(max_cutoff, max(low_cutoff + 0.001, high_cutoff))

    notch_values = sorted(
        {
            round(value, 6)
            for value in filter_settings.notch_frequencies_hz
            if 0.0 < float(value) < nyquist
        }
    )
    notch_q = max(0.1, float(filter_settings.notch_q))
    ripple_db = max(0.01, float(filter_settings.chebyshev1_ripple_db))
    layout_mode = _coerce_literal(
        settings.layout_mode,
        ("stacked", "expanded"),
        "expanded",
    )
    visible_channel_indices = _normalize_visible_channel_indices(
        settings.visible_channel_indices,
        channel_count,
    )
    if channel_count <= 1:
        layout_mode = "stacked"
    manual_y_min, manual_y_max = _normalize_manual_range(
        settings.manual_y_min,
        settings.manual_y_max,
    )

    return SignalPreviewSettings(
        window_seconds=window_seconds,
        antialias_enabled=bool(settings.antialias_enabled),
        layout_mode=layout_mode,
        visible_channel_indices=visible_channel_indices,
        y_range_mode=_coerce_literal(
            settings.y_range_mode,
            ("auto", "manual"),
            "auto",
        ),
        manual_y_min=manual_y_min,
        manual_y_max=manual_y_max,
        filter=SignalFilterSettings(
            family=_coerce_literal(
                filter_settings.family,
                ("butterworth", "chebyshev1", "bessel"),
                "butterworth",
            ),
            mode=_coerce_literal(
                filter_settings.mode,
                ("none", "low_pass", "high_pass", "band_pass", "band_stop"),
                "none",
            ),
            order=order,
            low_cutoff_hz=low_cutoff,
            high_cutoff_hz=high_cutoff,
            notch_enabled=bool(filter_settings.notch_enabled),
            notch_frequencies_hz=tuple(notch_values),
            notch_q=notch_q,
            chebyshev1_ripple_db=ripple_db,
        ),
    )


def _normalize_raster_settings(settings: RasterPreviewSettings) -> RasterPreviewSettings:
    manual_min, manual_max = _normalize_manual_range(
        settings.manual_min,
        settings.manual_max,
    )
    return RasterPreviewSettings(
        window_seconds=max(1, int(settings.window_seconds)),
        colormap=_coerce_str(settings.colormap, "gray"),
        value_range_mode=_coerce_literal(
            settings.value_range_mode,
            ("auto", "zero_to_one", "zero_to_255", "manual"),
            "auto",
        ),
        manual_min=manual_min,
        manual_max=manual_max,
        interpolation=_coerce_literal(
            settings.interpolation,
            ("nearest", "bilinear", "bicubic"),
            "nearest",
        ),
        transform=_coerce_literal(
            settings.transform,
            (
                "none",
                "flip_horizontal",
                "flip_vertical",
                "rotate_90",
                "rotate_180",
                "rotate_270",
            ),
            "none",
        ),
    )


def _normalize_field_settings(settings: FieldPreviewSettings) -> FieldPreviewSettings:
    manual_min, manual_max = _normalize_manual_range(
        settings.manual_min,
        settings.manual_max,
    )
    return FieldPreviewSettings(
        colormap=_coerce_str(settings.colormap, "gray"),
        value_range_mode=_coerce_literal(
            settings.value_range_mode,
            ("auto", "zero_to_one", "zero_to_255", "manual"),
            "auto",
        ),
        manual_min=manual_min,
        manual_max=manual_max,
        interpolation=_coerce_literal(
            settings.interpolation,
            ("nearest", "bilinear", "bicubic"),
            "nearest",
        ),
        transform=_coerce_literal(
            settings.transform,
            (
                "none",
                "flip_horizontal",
                "flip_vertical",
                "rotate_90",
                "rotate_180",
                "rotate_270",
            ),
            "none",
        ),
    )


def _normalize_video_settings(settings: VideoPreviewSettings) -> VideoPreviewSettings:
    return VideoPreviewSettings(
        color_format=_coerce_literal(
            settings.color_format,
            ("rgb", "bgr", "gray", "yuv"),
            "rgb",
        ),
        scale_mode=_coerce_literal(
            settings.scale_mode,
            ("fit", "fill"),
            "fit",
        ),
        aspect_mode=_coerce_literal(
            settings.aspect_mode,
            ("keep", "stretch"),
            "keep",
        ),
        transform=_coerce_literal(
            settings.transform,
            (
                "none",
                "flip_horizontal",
                "flip_vertical",
                "rotate_90",
                "rotate_180",
                "rotate_270",
            ),
            "none",
        ),
    )


def _normalize_manual_range(manual_min: float, manual_max: float) -> tuple[float, float]:
    low = float(manual_min)
    high = float(manual_max)
    if low > high:
        low, high = high, low
    if low == high:
        high = low + 1e-6
    return low, high


def _normalize_visible_channel_indices(
    visible_channel_indices: tuple[int, ...],
    channel_count: int,
) -> tuple[int, ...]:
    if channel_count <= 0:
        return ()

    requested = tuple(
        index
        for index in visible_channel_indices
        if isinstance(index, int) and 0 <= index < channel_count
    )
    if not requested:
        return tuple(range(channel_count))

    deduplicated = tuple(dict.fromkeys(requested))
    if not deduplicated:
        return tuple(range(channel_count))
    return deduplicated


def _coerce_int(value: object, default: int) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _coerce_float(value: object, default: float) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _coerce_str(value: object, default: str) -> str:
    if isinstance(value, str) and value:
        return value
    return default


def _coerce_float_tuple(value: object) -> tuple[float, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    result: list[float] = []
    for item in value:
        try:
            result.append(float(item))
        except (TypeError, ValueError):
            continue
    return tuple(result)


def _coerce_int_tuple(value: object) -> tuple[int, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    result: list[int] = []
    for item in value:
        try:
            result.append(int(item))
        except (TypeError, ValueError):
            continue
    return tuple(result)


def _coerce_literal(value: object, options: tuple[str, ...], default: str) -> str:
    if isinstance(value, str) and value in options:
        return value
    return default
