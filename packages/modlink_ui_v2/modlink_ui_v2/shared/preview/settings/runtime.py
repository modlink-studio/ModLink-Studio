from __future__ import annotations

from typing import cast

from PyQt6.QtWidgets import QWidget

from modlink_sdk import StreamDescriptor
from modlink_ui_v2.bridge import QtSettingsBridge

from ..views import (
    BaseStreamView,
    FieldStreamView,
    RasterStreamView,
    SignalStreamView,
    VideoStreamView,
)
from .dialog import StreamPreviewSettingsDialog
from .models import (
    FieldPreviewSettings,
    PreviewPayloadType,
    PreviewSettings,
    RasterPreviewSettings,
    SignalPreviewSettings,
    VideoPreviewSettings,
    normalize_preview_settings,
)
from .sections import (
    FieldPayloadSettingsPanel,
    RasterPayloadSettingsPanel,
    SignalPayloadSettingsPanel,
    VideoPayloadSettingsPanel,
)
from .store import PreviewStreamSettingsStore

type PreviewPayloadSectionWidget = (
    SignalPayloadSettingsPanel
    | RasterPayloadSettingsPanel
    | FieldPayloadSettingsPanel
    | VideoPayloadSettingsPanel
)

type SupportedPreviewStreamView = (
    SignalStreamView | RasterStreamView | FieldStreamView | VideoStreamView
)


class PreviewSettingsRuntime:
    def __init__(
        self,
        descriptor: StreamDescriptor,
        settings: QtSettingsBridge,
        stream_view: BaseStreamView,
        parent: QWidget | None = None,
    ) -> None:
        self.descriptor = descriptor
        self.parent = parent
        self.store = PreviewStreamSettingsStore(settings)
        self.payload_type = self._payload_type(descriptor)
        self.stream_view = self._coerce_stream_view(stream_view)
        self.payload_section_widget = self._create_payload_section()
        self.dialog: StreamPreviewSettingsDialog | None = None
        self._syncing_section = False

        self.payload_section_widget.sig_state_changed.connect(self._on_section_state_changed)
        self._apply_settings(self._load_settings())

    def open_dialog(self, parent: QWidget | None = None) -> None:
        dialog_parent = parent or self.parent
        if self.dialog is None:
            self.dialog = StreamPreviewSettingsDialog(
                self.descriptor,
                self.payload_section_widget,
                dialog_parent,
            )
        self.dialog.exec()

    def _load_settings(self) -> PreviewSettings:
        return self.store.load(self.descriptor)

    def _on_section_state_changed(self, state: object) -> None:
        if self._syncing_section:
            return

        settings = self._normalize_settings(state)
        self._apply_settings(settings)
        self.store.save(self.descriptor, settings)

    def _apply_settings(self, settings: PreviewSettings) -> None:
        self._set_section_state(settings)
        self._apply_to_view(settings)

    def _normalize_settings(self, state: object) -> PreviewSettings:
        sample_rate_hz = float(self.descriptor.nominal_sample_rate_hz or 1.0)
        channel_names = tuple(self.descriptor.channel_names)
        if self.payload_type == "signal":
            if not isinstance(state, SignalPreviewSettings):
                raise TypeError("signal preview settings must use SignalPreviewSettings")
            return normalize_preview_settings(
                "signal",
                state,
                sample_rate_hz,
                channel_names,
            )
        if self.payload_type == "raster":
            if not isinstance(state, RasterPreviewSettings):
                raise TypeError("raster preview settings must use RasterPreviewSettings")
            return normalize_preview_settings(
                "raster",
                state,
                sample_rate_hz,
                channel_names,
            )
        if self.payload_type == "field":
            if not isinstance(state, FieldPreviewSettings):
                raise TypeError("field preview settings must use FieldPreviewSettings")
            return normalize_preview_settings(
                "field",
                state,
                sample_rate_hz,
                channel_names,
            )
        if self.payload_type == "video":
            if not isinstance(state, VideoPreviewSettings):
                raise TypeError("video preview settings must use VideoPreviewSettings")
            return normalize_preview_settings(
                "video",
                state,
                sample_rate_hz,
                channel_names,
            )
        raise ValueError(f"unsupported payload_type: {self.payload_type}")

    def _set_section_state(self, settings: PreviewSettings) -> None:
        self._syncing_section = True
        try:
            if self.payload_type == "signal":
                assert isinstance(settings, SignalPreviewSettings)
                self.payload_section_widget.set_state(settings)
            elif self.payload_type == "raster":
                assert isinstance(settings, RasterPreviewSettings)
                self.payload_section_widget.set_state(settings)
            elif self.payload_type == "field":
                assert isinstance(settings, FieldPreviewSettings)
                self.payload_section_widget.set_state(settings)
            else:
                assert isinstance(settings, VideoPreviewSettings)
                self.payload_section_widget.set_state(settings)
        finally:
            self._syncing_section = False

    def _apply_to_view(self, settings: PreviewSettings) -> None:
        if self.payload_type == "signal":
            assert isinstance(settings, SignalPreviewSettings)
            self.stream_view.apply_preview_settings(settings)
            return
        if self.payload_type == "raster":
            assert isinstance(settings, RasterPreviewSettings)
            self.stream_view.apply_preview_settings(settings)
            return
        if self.payload_type == "field":
            assert isinstance(settings, FieldPreviewSettings)
            self.stream_view.apply_preview_settings(settings)
            return
        assert isinstance(settings, VideoPreviewSettings)
        self.stream_view.apply_preview_settings(settings)

    def _create_payload_section(self) -> PreviewPayloadSectionWidget:
        if self.payload_type == "signal":
            return SignalPayloadSettingsPanel(self.descriptor, None)
        if self.payload_type == "raster":
            return RasterPayloadSettingsPanel(self.descriptor, None)
        if self.payload_type == "field":
            return FieldPayloadSettingsPanel(self.descriptor, None)
        if self.payload_type == "video":
            return VideoPayloadSettingsPanel(self.descriptor, None)
        raise ValueError(f"unsupported payload_type: {self.payload_type}")

    def _coerce_stream_view(self, stream_view: BaseStreamView) -> SupportedPreviewStreamView:
        if self.payload_type == "signal":
            if not isinstance(stream_view, SignalStreamView):
                raise TypeError("signal preview runtime requires SignalStreamView")
            return stream_view
        if self.payload_type == "raster":
            if not isinstance(stream_view, RasterStreamView):
                raise TypeError("raster preview runtime requires RasterStreamView")
            return stream_view
        if self.payload_type == "field":
            if not isinstance(stream_view, FieldStreamView):
                raise TypeError("field preview runtime requires FieldStreamView")
            return stream_view
        if self.payload_type == "video":
            if not isinstance(stream_view, VideoStreamView):
                raise TypeError("video preview runtime requires VideoStreamView")
            return stream_view
        raise ValueError(f"unsupported payload_type: {self.payload_type}")

    @staticmethod
    def _payload_type(descriptor: StreamDescriptor) -> PreviewPayloadType:
        payload_type = str(descriptor.payload_type)
        if payload_type not in {"signal", "raster", "field", "video"}:
            raise ValueError(f"unsupported payload_type: {payload_type}")
        return cast(PreviewPayloadType, payload_type)
