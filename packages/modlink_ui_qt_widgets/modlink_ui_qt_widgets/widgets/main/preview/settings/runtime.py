from __future__ import annotations

from typing import cast

from PyQt6.QtWidgets import QWidget

from modlink_qt_bridge import QtSettingsBridge
from modlink_sdk import StreamDescriptor

from .dialog import StreamPreviewSettingsDialog
from .models import (
    PreviewPayloadType,
    PreviewSettings,
    default_preview_settings,
    normalize_preview_settings,
)
from .sections import create_payload_settings_section
from .store import PreviewStreamSettingsStore


class PreviewSettingsRuntime:
    def __init__(
        self,
        descriptor: StreamDescriptor,
        settings: QtSettingsBridge,
        stream_view: QWidget,
        parent: QWidget | None = None,
    ) -> None:
        self.descriptor = descriptor
        self.stream_view = stream_view
        self.parent = parent
        self.store = PreviewStreamSettingsStore(settings)
        self.payload_type = self._payload_type(descriptor)
        self.payload_section_widget = create_payload_settings_section(descriptor, None)
        self.dialog: StreamPreviewSettingsDialog | None = None
        self._syncing_section = False

        self._connect_section_signal()
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

    def _connect_section_signal(self) -> None:
        signal = getattr(self.payload_section_widget, "sig_state_changed", None)
        if signal is None:
            raise TypeError(
                f"{type(self.payload_section_widget).__name__} must expose sig_state_changed"
            )
        signal.connect(self._on_section_state_changed)

    def _load_settings(self) -> PreviewSettings:
        return self._normalize_settings(self.store.load(self.descriptor))

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
        settings = self._coerce_settings(state)
        return normalize_preview_settings(
            self.payload_type,
            settings,
            float(self.descriptor.nominal_sample_rate_hz or 1.0),
            tuple(self.descriptor.channel_names),
        )

    def _coerce_settings(self, state: object) -> PreviewSettings:
        default = default_preview_settings(self.payload_type)
        if isinstance(state, type(default)):
            return cast(PreviewSettings, state)
        return default

    def _set_section_state(self, settings: PreviewSettings) -> None:
        set_state = getattr(self.payload_section_widget, "set_state", None)
        if not callable(set_state):
            raise TypeError(
                f"{type(self.payload_section_widget).__name__} must implement set_state()"
            )

        self._syncing_section = True
        try:
            set_state(settings)
        finally:
            self._syncing_section = False

    def _apply_to_view(self, settings: PreviewSettings) -> None:
        apply_preview_settings = getattr(self.stream_view, "apply_preview_settings", None)
        if callable(apply_preview_settings):
            apply_preview_settings(settings)

    @staticmethod
    def _payload_type(descriptor: StreamDescriptor) -> PreviewPayloadType:
        payload_type = str(descriptor.payload_type)
        if payload_type not in {"signal", "raster", "field", "video"}:
            raise ValueError(f"unsupported payload_type: {payload_type}")
        return cast(PreviewPayloadType, payload_type)
