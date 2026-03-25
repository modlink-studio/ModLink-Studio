from __future__ import annotations

from typing import Any, cast

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QWidget

from modlink_sdk import StreamDescriptor

from .adapters import (
    FieldViewSettingsAdapter,
    RasterViewSettingsAdapter,
    SignalViewSettingsAdapter,
    VideoViewSettingsAdapter,
)
from .controllers import (
    FieldSettingsController,
    RasterSettingsController,
    SignalSettingsController,
    VideoSettingsController,
)
from .dialog import StreamPreviewSettingsDialog
from .models import (
    FieldPreviewSettings,
    PreviewPayloadType,
    RasterPreviewSettings,
    SignalFilterSettings,
    SignalPreviewSettings,
    VideoPreviewSettings,
)
from .sections import create_payload_settings_section
from .store import PreviewStreamSettingsStore


class PreviewSettingsRuntime:
    def __init__(
        self,
        descriptor: StreamDescriptor,
        stream_view: QWidget,
        parent: QWidget | None = None,
    ) -> None:
        self.descriptor = descriptor
        self.stream_view = stream_view
        self.parent = parent
        self.store = PreviewStreamSettingsStore()
        self.payload_section_widget = create_payload_settings_section(descriptor, None)
        self.dialog: StreamPreviewSettingsDialog | None = None

        payload_type = self._payload_type(descriptor)
        if payload_type == "signal":
            section = _adapt_signal_section(self.payload_section_widget)
            self.controller = SignalSettingsController(
                descriptor=descriptor,
                section=section,
                stream_view=stream_view,
                store=self.store,
                adapter=SignalViewSettingsAdapter(),
            )
        elif payload_type == "raster":
            section = _adapt_raster_section(self.payload_section_widget)
            self.controller = RasterSettingsController(
                descriptor=descriptor,
                section=section,
                stream_view=stream_view,
                store=self.store,
                adapter=RasterViewSettingsAdapter(),
            )
        elif payload_type == "field":
            section = _adapt_field_section(self.payload_section_widget)
            self.controller = FieldSettingsController(
                descriptor=descriptor,
                section=section,
                stream_view=stream_view,
                store=self.store,
                adapter=FieldViewSettingsAdapter(),
            )
        elif payload_type == "video":
            section = _adapt_video_section(self.payload_section_widget)
            self.controller = VideoSettingsController(
                descriptor=descriptor,
                section=section,
                stream_view=stream_view,
                store=self.store,
                adapter=VideoViewSettingsAdapter(),
            )
        else:
            raise ValueError(f"unsupported payload_type: {payload_type}")

        self.controller.initialize()

    def open_dialog(self, parent: QWidget | None = None) -> None:
        dialog_parent = parent or self.parent
        if self.dialog is None:
            self.dialog = StreamPreviewSettingsDialog(
                self.descriptor,
                self.payload_section_widget,
                dialog_parent,
            )
        self.dialog.exec()

    @staticmethod
    def _payload_type(descriptor: StreamDescriptor) -> PreviewPayloadType:
        payload_type = str(descriptor.payload_type)
        if payload_type not in {"signal", "raster", "field", "video"}:
            raise ValueError(f"unsupported payload_type: {payload_type}")
        return cast(PreviewPayloadType, payload_type)


class _SectionBridgeBase(QObject):
    sig_state_changed = pyqtSignal(object)

    def __init__(self, section_widget: QWidget) -> None:
        super().__init__(section_widget)
        self.section_widget = section_widget

    def _emit_state_changed(self) -> None:
        self.sig_state_changed.emit(self.state())


class _SignalSectionBridge(_SectionBridgeBase):
    def __init__(self, section_widget: QWidget) -> None:
        super().__init__(section_widget)
        self._connect_controls()

    def set_state(self, settings: SignalPreviewSettings) -> None:
        _set_combo_data(self.section_widget, "duration_combo", settings.window_seconds)
        _set_checked(
            self.section_widget,
            "antialias_switch",
            settings.antialias_enabled,
        )
        _set_combo_data(self.section_widget, "filter_mode_combo", settings.filter.mode)
        _set_combo_data(self.section_widget, "filter_family_combo", settings.filter.family)
        _set_spin_value(self.section_widget, "filter_order_spinbox", settings.filter.order)
        _set_spin_value(
            self.section_widget,
            "low_cutoff_spinbox",
            int(round(settings.filter.low_cutoff_hz)),
        )
        _set_spin_value(
            self.section_widget,
            "high_cutoff_spinbox",
            int(round(settings.filter.high_cutoff_hz)),
        )
        _set_checked(self.section_widget, "notch_enabled_switch", settings.filter.notch_enabled)
        _set_tokens(
            self.section_widget,
            "notch_frequencies_edit",
            [f"{value:g}" for value in settings.filter.notch_frequencies_hz],
        )

    def state(self) -> SignalPreviewSettings:
        notch_tokens = _tokens(self.section_widget, "notch_frequencies_edit")
        notch_values: list[float] = []
        for token in notch_tokens:
            try:
                notch_values.append(float(token))
            except (TypeError, ValueError):
                continue
        return SignalPreviewSettings(
            window_seconds=int(_combo_data(self.section_widget, "duration_combo", 8)),
            antialias_enabled=bool(
                _checked(self.section_widget, "antialias_switch", True)
            ),
            filter=SignalFilterSettings(
                family=cast(
                    Any,
                    _combo_data(
                        self.section_widget,
                        "filter_family_combo",
                        "butterworth",
                    ),
                ),
                mode=cast(
                    Any,
                    _combo_data(
                        self.section_widget,
                        "filter_mode_combo",
                        "none",
                    ),
                ),
                order=int(_spin_value(self.section_widget, "filter_order_spinbox", 4)),
                low_cutoff_hz=float(_spin_value(self.section_widget, "low_cutoff_spinbox", 1)),
                high_cutoff_hz=float(
                    _spin_value(self.section_widget, "high_cutoff_spinbox", 40)
                ),
                notch_enabled=bool(
                    _checked(self.section_widget, "notch_enabled_switch", False)
                ),
                notch_frequencies_hz=tuple(notch_values),
                notch_q=30.0,
                chebyshev1_ripple_db=1.0,
            ),
        )

    def _connect_controls(self) -> None:
        _connect_signal(self.section_widget, "duration_combo", "currentIndexChanged", self._emit_state_changed)
        _connect_signal(self.section_widget, "antialias_switch", "checkedChanged", self._emit_state_changed)
        _connect_signal(self.section_widget, "filter_mode_combo", "currentIndexChanged", self._emit_state_changed)
        _connect_signal(self.section_widget, "filter_family_combo", "currentIndexChanged", self._emit_state_changed)
        _connect_signal(self.section_widget, "filter_order_spinbox", "valueChanged", self._emit_state_changed)
        _connect_signal(self.section_widget, "low_cutoff_spinbox", "valueChanged", self._emit_state_changed)
        _connect_signal(self.section_widget, "high_cutoff_spinbox", "valueChanged", self._emit_state_changed)
        _connect_signal(self.section_widget, "notch_enabled_switch", "checkedChanged", self._emit_state_changed)
        _connect_signal(self.section_widget, "notch_frequencies_edit", "sig_tokens_changed", self._emit_state_changed)


class _RasterSectionBridge(_SectionBridgeBase):
    def __init__(self, section_widget: QWidget) -> None:
        super().__init__(section_widget)
        self._connect_controls()

    def set_state(self, settings: RasterPreviewSettings) -> None:
        _set_combo_data(self.section_widget, "duration_combo", settings.window_seconds)
        _set_combo_data(self.section_widget, "colormap_combo", settings.colormap)
        _set_combo_data(self.section_widget, "value_range_combo", settings.value_range_mode)
        _set_spin_value(self.section_widget, "manual_min_spinbox", int(round(settings.manual_min)))
        _set_spin_value(self.section_widget, "manual_max_spinbox", int(round(settings.manual_max)))
        _set_combo_data(self.section_widget, "interpolation_combo", settings.interpolation)
        _set_combo_data(self.section_widget, "transform_combo", settings.transform)

    def state(self) -> RasterPreviewSettings:
        return RasterPreviewSettings(
            window_seconds=int(_combo_data(self.section_widget, "duration_combo", 8)),
            colormap=str(_combo_data(self.section_widget, "colormap_combo", "gray")),
            value_range_mode=cast(
                Any,
                _combo_data(self.section_widget, "value_range_combo", "auto"),
            ),
            manual_min=float(_spin_value(self.section_widget, "manual_min_spinbox", 0)),
            manual_max=float(_spin_value(self.section_widget, "manual_max_spinbox", 1)),
            interpolation=cast(
                Any,
                _combo_data(self.section_widget, "interpolation_combo", "nearest"),
            ),
            transform=cast(
                Any,
                _combo_data(self.section_widget, "transform_combo", "none"),
            ),
        )

    def _connect_controls(self) -> None:
        _connect_signal(self.section_widget, "duration_combo", "currentIndexChanged", self._emit_state_changed)
        _connect_signal(self.section_widget, "colormap_combo", "currentIndexChanged", self._emit_state_changed)
        _connect_signal(self.section_widget, "value_range_combo", "currentIndexChanged", self._emit_state_changed)
        _connect_signal(self.section_widget, "manual_min_spinbox", "valueChanged", self._emit_state_changed)
        _connect_signal(self.section_widget, "manual_max_spinbox", "valueChanged", self._emit_state_changed)
        _connect_signal(self.section_widget, "interpolation_combo", "currentIndexChanged", self._emit_state_changed)
        _connect_signal(self.section_widget, "transform_combo", "currentIndexChanged", self._emit_state_changed)


class _FieldSectionBridge(_SectionBridgeBase):
    def __init__(self, section_widget: QWidget) -> None:
        super().__init__(section_widget)
        self._connect_controls()

    def set_state(self, settings: FieldPreviewSettings) -> None:
        _set_combo_data(self.section_widget, "colormap_combo", settings.colormap)
        _set_combo_data(self.section_widget, "value_range_combo", settings.value_range_mode)
        _set_spin_value(self.section_widget, "manual_min_spinbox", int(round(settings.manual_min)))
        _set_spin_value(self.section_widget, "manual_max_spinbox", int(round(settings.manual_max)))
        _set_combo_data(self.section_widget, "interpolation_combo", settings.interpolation)
        _set_combo_data(self.section_widget, "transform_combo", settings.transform)

    def state(self) -> FieldPreviewSettings:
        return FieldPreviewSettings(
            colormap=str(_combo_data(self.section_widget, "colormap_combo", "gray")),
            value_range_mode=cast(
                Any,
                _combo_data(self.section_widget, "value_range_combo", "auto"),
            ),
            manual_min=float(_spin_value(self.section_widget, "manual_min_spinbox", 0)),
            manual_max=float(_spin_value(self.section_widget, "manual_max_spinbox", 1)),
            interpolation=cast(
                Any,
                _combo_data(self.section_widget, "interpolation_combo", "nearest"),
            ),
            transform=cast(
                Any,
                _combo_data(self.section_widget, "transform_combo", "none"),
            ),
        )

    def _connect_controls(self) -> None:
        _connect_signal(self.section_widget, "colormap_combo", "currentIndexChanged", self._emit_state_changed)
        _connect_signal(self.section_widget, "value_range_combo", "currentIndexChanged", self._emit_state_changed)
        _connect_signal(self.section_widget, "manual_min_spinbox", "valueChanged", self._emit_state_changed)
        _connect_signal(self.section_widget, "manual_max_spinbox", "valueChanged", self._emit_state_changed)
        _connect_signal(self.section_widget, "interpolation_combo", "currentIndexChanged", self._emit_state_changed)
        _connect_signal(self.section_widget, "transform_combo", "currentIndexChanged", self._emit_state_changed)


class _VideoSectionBridge(_SectionBridgeBase):
    def __init__(self, section_widget: QWidget) -> None:
        super().__init__(section_widget)
        self._connect_controls()

    def set_state(self, settings: VideoPreviewSettings) -> None:
        _set_combo_data(self.section_widget, "color_format_combo", settings.color_format)
        _set_combo_data(self.section_widget, "scale_mode_combo", settings.scale_mode)
        if hasattr(self.section_widget, "aspect_mode_combo"):
            _set_combo_data(self.section_widget, "aspect_mode_combo", settings.aspect_mode)
        else:
            _set_combo_data(self.section_widget, "aspect_ratio_combo", settings.aspect_mode)
        _set_combo_data(self.section_widget, "transform_combo", settings.transform)

    def state(self) -> VideoPreviewSettings:
        aspect_name = (
            "aspect_mode_combo"
            if hasattr(self.section_widget, "aspect_mode_combo")
            else "aspect_ratio_combo"
        )
        return VideoPreviewSettings(
            color_format=cast(
                Any,
                _combo_data(self.section_widget, "color_format_combo", "rgb"),
            ),
            scale_mode=cast(
                Any,
                _combo_data(self.section_widget, "scale_mode_combo", "fit"),
            ),
            aspect_mode=cast(
                Any,
                _combo_data(self.section_widget, aspect_name, "keep"),
            ),
            transform=cast(
                Any,
                _combo_data(self.section_widget, "transform_combo", "none"),
            ),
        )

    def _connect_controls(self) -> None:
        _connect_signal(self.section_widget, "color_format_combo", "currentIndexChanged", self._emit_state_changed)
        _connect_signal(self.section_widget, "scale_mode_combo", "currentIndexChanged", self._emit_state_changed)
        if hasattr(self.section_widget, "aspect_mode_combo"):
            _connect_signal(self.section_widget, "aspect_mode_combo", "currentIndexChanged", self._emit_state_changed)
        else:
            _connect_signal(self.section_widget, "aspect_ratio_combo", "currentIndexChanged", self._emit_state_changed)
        _connect_signal(self.section_widget, "transform_combo", "currentIndexChanged", self._emit_state_changed)


def _adapt_signal_section(section_widget: QWidget) -> Any:
    return _SignalSectionBridge(section_widget)


def _adapt_raster_section(section_widget: QWidget) -> Any:
    return _RasterSectionBridge(section_widget)


def _adapt_field_section(section_widget: QWidget) -> Any:
    return _FieldSectionBridge(section_widget)


def _adapt_video_section(section_widget: QWidget) -> Any:
    return _VideoSectionBridge(section_widget)


def _connect_signal(widget: QWidget, attr_name: str, signal_name: str, slot: Any) -> None:
    control = getattr(widget, attr_name, None)
    if control is None:
        return
    signal = getattr(control, signal_name, None)
    if signal is None:
        return
    signal.connect(slot)


def _combo_data(widget: QWidget, attr_name: str, default: object) -> object:
    combo = getattr(widget, attr_name, None)
    if combo is None:
        return default
    value = combo.currentData()
    return default if value is None else value


def _set_combo_data(widget: QWidget, attr_name: str, value: object) -> None:
    combo = getattr(widget, attr_name, None)
    if combo is None:
        return
    for index in range(combo.count()):
        if combo.itemData(index) == value:
            combo.setCurrentIndex(index)
            return


def _spin_value(widget: QWidget, attr_name: str, default: float) -> float:
    spinbox = getattr(widget, attr_name, None)
    if spinbox is None:
        return default
    return float(spinbox.value())


def _set_spin_value(widget: QWidget, attr_name: str, value: int) -> None:
    spinbox = getattr(widget, attr_name, None)
    if spinbox is None:
        return
    spinbox.setValue(value)


def _checked(widget: QWidget, attr_name: str, default: bool) -> bool:
    control = getattr(widget, attr_name, None)
    if control is None:
        return default
    if hasattr(control, "isChecked"):
        return bool(control.isChecked())
    return default


def _set_checked(widget: QWidget, attr_name: str, value: bool) -> None:
    control = getattr(widget, attr_name, None)
    if control is None:
        return
    if hasattr(control, "setChecked"):
        control.setChecked(value)


def _tokens(widget: QWidget, attr_name: str) -> list[str]:
    token_edit = getattr(widget, attr_name, None)
    if token_edit is None:
        return []
    if hasattr(token_edit, "tokens"):
        return list(token_edit.tokens())
    return []


def _set_tokens(widget: QWidget, attr_name: str, values: list[str]) -> None:
    token_edit = getattr(widget, attr_name, None)
    if token_edit is None:
        return
    if hasattr(token_edit, "set_tokens"):
        token_edit.set_tokens(values)
