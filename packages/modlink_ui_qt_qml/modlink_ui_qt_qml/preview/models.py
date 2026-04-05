from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal, TypeAlias

PreviewPayloadType: TypeAlias = Literal["signal", "raster", "field", "video"]

SignalFilterFamily: TypeAlias = Literal["butterworth", "chebyshev1", "bessel"]
SignalFilterMode: TypeAlias = Literal[
    "none", "low_pass", "high_pass", "band_pass", "band_stop",
]
SignalLayoutMode: TypeAlias = Literal["stacked", "expanded"]
ValueRangeMode: TypeAlias = Literal["auto", "zero_to_one", "zero_to_255", "manual"]
SignalYAxisRangeMode: TypeAlias = Literal["auto", "manual"]
InterpolationMode: TypeAlias = Literal["nearest", "bilinear", "bicubic"]
TransformMode: TypeAlias = Literal[
    "none", "flip_horizontal", "flip_vertical",
    "rotate_90", "rotate_180", "rotate_270",
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
        vci = payload.get("visible_channel_indices", [])
        if isinstance(vci, tuple):
            payload["visible_channel_indices"] = list(vci)
        filter_payload = payload.get("filter", {})
        if isinstance(filter_payload, dict):
            freqs = filter_payload.get("notch_frequencies_hz", [])
            if isinstance(freqs, (list, tuple)):
                filter_payload["notch_frequencies_hz"] = list(freqs)
            payload["filter"] = filter_payload
    return payload


def deserialize_preview_settings(
    payload_type: PreviewPayloadType,
    payload: object,
) -> PreviewSettings:
    if not isinstance(payload, dict):
        return default_preview_settings(payload_type)

    if payload_type == "signal":
        fp = payload.get("filter")
        if not isinstance(fp, dict):
            fp = {}
        return SignalPreviewSettings(
            window_seconds=_int(payload.get("window_seconds"), 8),
            antialias_enabled=bool(payload.get("antialias_enabled", True)),
            layout_mode=_literal(payload.get("layout_mode"), ("stacked", "expanded"), "expanded"),
            visible_channel_indices=_int_tuple(payload.get("visible_channel_indices")),
            y_range_mode=_literal(payload.get("y_range_mode"), ("auto", "manual"), "auto"),
            manual_y_min=_float(payload.get("manual_y_min"), -1.0),
            manual_y_max=_float(payload.get("manual_y_max"), 1.0),
            filter=SignalFilterSettings(
                family=_literal(fp.get("family"), ("butterworth", "chebyshev1", "bessel"), "butterworth"),
                mode=_literal(fp.get("mode"), ("none", "low_pass", "high_pass", "band_pass", "band_stop"), "none"),
                order=_int(fp.get("order"), 4),
                low_cutoff_hz=_float(fp.get("low_cutoff_hz"), 1.0),
                high_cutoff_hz=_float(fp.get("high_cutoff_hz"), 40.0),
                notch_enabled=bool(fp.get("notch_enabled", False)),
                notch_frequencies_hz=_float_tuple(fp.get("notch_frequencies_hz", ())),
                notch_q=_float(fp.get("notch_q"), 30.0),
                chebyshev1_ripple_db=_float(fp.get("chebyshev1_ripple_db"), 1.0),
            ),
        )

    if payload_type == "raster":
        return RasterPreviewSettings(
            window_seconds=_int(payload.get("window_seconds"), 8),
            colormap=_str(payload.get("colormap"), "gray"),
            value_range_mode=_literal(payload.get("value_range_mode"), ("auto", "zero_to_one", "zero_to_255", "manual"), "auto"),
            manual_min=_float(payload.get("manual_min"), 0.0),
            manual_max=_float(payload.get("manual_max"), 1.0),
            interpolation=_literal(payload.get("interpolation"), ("nearest", "bilinear", "bicubic"), "nearest"),
            transform=_literal(payload.get("transform"), _TRANSFORMS, "none"),
        )

    if payload_type == "field":
        return FieldPreviewSettings(
            colormap=_str(payload.get("colormap"), "gray"),
            value_range_mode=_literal(payload.get("value_range_mode"), ("auto", "zero_to_one", "zero_to_255", "manual"), "auto"),
            manual_min=_float(payload.get("manual_min"), 0.0),
            manual_max=_float(payload.get("manual_max"), 1.0),
            interpolation=_literal(payload.get("interpolation"), ("nearest", "bilinear", "bicubic"), "nearest"),
            transform=_literal(payload.get("transform"), _TRANSFORMS, "none"),
        )

    if payload_type == "video":
        return VideoPreviewSettings(
            color_format=_literal(payload.get("color_format"), ("rgb", "bgr", "gray", "yuv"), "rgb"),
            scale_mode=_literal(payload.get("scale_mode"), ("fit", "fill"), "fit"),
            aspect_mode=_literal(payload.get("aspect_mode"), ("keep", "stretch"), "keep"),
            transform=_literal(payload.get("transform"), _TRANSFORMS, "none"),
        )

    raise ValueError(f"unsupported payload_type: {payload_type}")


def normalize_preview_settings(
    payload_type: PreviewPayloadType,
    settings: PreviewSettings,
    nominal_sample_rate_hz: float,
    channel_names: tuple[str, ...] = (),
) -> PreviewSettings:
    if payload_type == "signal" and isinstance(settings, SignalPreviewSettings):
        return _normalize_signal(settings, nominal_sample_rate_hz, channel_names)
    if payload_type == "raster" and isinstance(settings, RasterPreviewSettings):
        return _normalize_raster(settings)
    if payload_type == "field" and isinstance(settings, FieldPreviewSettings):
        return _normalize_field(settings)
    if payload_type == "video" and isinstance(settings, VideoPreviewSettings):
        return _normalize_video(settings)
    raise ValueError(f"unsupported payload_type: {payload_type}")


_TRANSFORMS = ("none", "flip_horizontal", "flip_vertical", "rotate_90", "rotate_180", "rotate_270")


def _normalize_signal(
    s: SignalPreviewSettings,
    sr: float,
    ch_names: tuple[str, ...],
) -> SignalPreviewSettings:
    nyq = max(float(sr or 1.0) / 2.0, 1.0)
    ch_count = max(len(ch_names), 0)
    f = s.filter
    order = min(max(int(f.order), 1), 12)
    max_cutoff = max(0.001, nyq - 1e-6)
    lo = max(0.001, min(float(f.low_cutoff_hz), max_cutoff))
    hi = max(0.001, min(float(f.high_cutoff_hz), max_cutoff))
    if lo > hi:
        lo, hi = hi, lo
    if f.mode in ("band_pass", "band_stop") and lo >= hi:
        lo = max(0.001, min(lo, max_cutoff * 0.5))
        hi = min(max_cutoff, max(lo + 0.001, hi))

    notch = sorted({round(v, 6) for v in f.notch_frequencies_hz if 0.0 < float(v) < nyq})
    layout = _literal(s.layout_mode, ("stacked", "expanded"), "expanded")
    vci = _normalize_vci(s.visible_channel_indices, ch_count)
    if ch_count <= 1:
        layout = "stacked"
    y_lo, y_hi = _normalize_range(s.manual_y_min, s.manual_y_max)

    return SignalPreviewSettings(
        window_seconds=max(1, int(s.window_seconds)),
        antialias_enabled=bool(s.antialias_enabled),
        layout_mode=layout,
        visible_channel_indices=vci,
        y_range_mode=_literal(s.y_range_mode, ("auto", "manual"), "auto"),
        manual_y_min=y_lo,
        manual_y_max=y_hi,
        filter=SignalFilterSettings(
            family=_literal(f.family, ("butterworth", "chebyshev1", "bessel"), "butterworth"),
            mode=_literal(f.mode, ("none", "low_pass", "high_pass", "band_pass", "band_stop"), "none"),
            order=order,
            low_cutoff_hz=lo,
            high_cutoff_hz=hi,
            notch_enabled=bool(f.notch_enabled),
            notch_frequencies_hz=tuple(notch),
            notch_q=max(0.1, float(f.notch_q)),
            chebyshev1_ripple_db=max(0.01, float(f.chebyshev1_ripple_db)),
        ),
    )


def _normalize_raster(s: RasterPreviewSettings) -> RasterPreviewSettings:
    lo, hi = _normalize_range(s.manual_min, s.manual_max)
    return RasterPreviewSettings(
        window_seconds=max(1, int(s.window_seconds)),
        colormap=_str(s.colormap, "gray"),
        value_range_mode=_literal(s.value_range_mode, ("auto", "zero_to_one", "zero_to_255", "manual"), "auto"),
        manual_min=lo, manual_max=hi,
        interpolation=_literal(s.interpolation, ("nearest", "bilinear", "bicubic"), "nearest"),
        transform=_literal(s.transform, _TRANSFORMS, "none"),
    )


def _normalize_field(s: FieldPreviewSettings) -> FieldPreviewSettings:
    lo, hi = _normalize_range(s.manual_min, s.manual_max)
    return FieldPreviewSettings(
        colormap=_str(s.colormap, "gray"),
        value_range_mode=_literal(s.value_range_mode, ("auto", "zero_to_one", "zero_to_255", "manual"), "auto"),
        manual_min=lo, manual_max=hi,
        interpolation=_literal(s.interpolation, ("nearest", "bilinear", "bicubic"), "nearest"),
        transform=_literal(s.transform, _TRANSFORMS, "none"),
    )


def _normalize_video(s: VideoPreviewSettings) -> VideoPreviewSettings:
    return VideoPreviewSettings(
        color_format=_literal(s.color_format, ("rgb", "bgr", "gray", "yuv"), "rgb"),
        scale_mode=_literal(s.scale_mode, ("fit", "fill"), "fit"),
        aspect_mode=_literal(s.aspect_mode, ("keep", "stretch"), "keep"),
        transform=_literal(s.transform, _TRANSFORMS, "none"),
    )


def _normalize_vci(vci: tuple[int, ...], ch_count: int) -> tuple[int, ...]:
    if ch_count <= 0:
        return ()
    requested = tuple(dict.fromkeys(i for i in vci if isinstance(i, int) and 0 <= i < ch_count))
    return requested or tuple(range(ch_count))


def _normalize_range(lo: float, hi: float) -> tuple[float, float]:
    lo, hi = float(lo), float(hi)
    if lo > hi:
        lo, hi = hi, lo
    if lo == hi:
        hi = lo + 1e-6
    return lo, hi


def _int(v: object, d: int) -> int:
    try:
        return int(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return d


def _float(v: object, d: float) -> float:
    try:
        return float(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return d


def _str(v: object, d: str) -> str:
    return v if isinstance(v, str) and v else d


def _literal(v: object, options: tuple[str, ...], d: str) -> str:
    return v if isinstance(v, str) and v in options else d


def _float_tuple(v: object) -> tuple[float, ...]:
    if not isinstance(v, (list, tuple)):
        return ()
    result: list[float] = []
    for item in v:
        try:
            result.append(float(item))
        except (TypeError, ValueError):
            pass
    return tuple(result)


def _int_tuple(v: object) -> tuple[int, ...]:
    if not isinstance(v, (list, tuple)):
        return ()
    result: list[int] = []
    for item in v:
        try:
            result.append(int(item))
        except (TypeError, ValueError):
            pass
    return tuple(result)
