from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from PyQt6.QtCore import QObject, QTimer, pyqtProperty, pyqtSignal

from modlink_qt_bridge import QtModLinkBridge
from modlink_sdk import FrameEnvelope, StreamDescriptor

from .acquisition import AcquisitionController
from .constants import (
    DEFAULT_PREVIEW_REFRESH_RATE_HZ,
    UI_PREVIEW_REFRESH_RATE_HZ_KEY,
    normalize_preview_refresh_rate_hz,
)
from .helpers import format_timestamp_ns
from .preview.models import (
    PreviewSettings,
    default_preview_settings,
    normalize_preview_settings,
)
from .preview.store import PreviewStreamSettingsStore
from .preview.stream_controller_factory import (
    StreamController,
    apply_settings_to_controller,
    create_stream_controller,
)


@dataclass(slots=True)
class _StreamState:
    descriptor: StreamDescriptor
    controller: StreamController
    frame_count: int = 0
    last_timestamp_ns: int | None = None
    summary_text: str = "等待数据"
    dirty: bool = False


class MainPageController(QObject):
    previewsChanged = pyqtSignal()
    messageRaised = pyqtSignal(str)

    def __init__(self, engine: QtModLinkBridge, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._engine = engine
        self._settings = engine.settings
        self._acquisition = AcquisitionController(engine, parent=self)
        self._store = PreviewStreamSettingsStore(self._settings)
        self._streams: dict[str, _StreamState] = {}
        self._stream_order: list[str] = []

        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._flush_previews)
        self._apply_refresh_rate()

        self._acquisition.messageRaised.connect(self.messageRaised.emit)
        self._engine.bus.sig_frame.connect(self._on_frame)
        self._settings.sig_setting_changed.connect(self._on_setting_changed)

        for descriptor in self._engine.bus.descriptors().values():
            self._ensure_stream(descriptor)

    @pyqtProperty(QObject, constant=True)
    def acquisition(self) -> QObject:
        return self._acquisition

    @pyqtProperty("QVariantList", notify=previewsChanged)
    def previews(self) -> list[dict[str, object]]:
        result = []
        for stream_id in self._stream_order:
            state = self._streams.get(stream_id)
            if state is None:
                continue
            desc = state.descriptor
            ctrl = state.controller
            result.append({
                "streamId": desc.stream_id,
                "displayName": desc.display_name or desc.stream_id,
                "payloadType": desc.payload_type,
                "summaryText": state.summary_text,
                "frameCount": state.frame_count,
                "channelSummary": ", ".join(desc.channel_names) or "无 channel 标签",
                "sampleRateText": f"{desc.nominal_sample_rate_hz:g} Hz",
                "controller": ctrl,
            })
        return result

    def _ensure_stream(self, descriptor: StreamDescriptor) -> _StreamState:
        existing = self._streams.get(descriptor.stream_id)
        if existing is not None:
            return existing

        controller = create_stream_controller(descriptor, parent=self)
        state = _StreamState(descriptor=descriptor, controller=controller)
        self._streams[descriptor.stream_id] = state

        settings = self._store.load(descriptor)
        apply_settings_to_controller(controller, settings)

        self._stream_order = sorted(
            self._streams.keys(),
            key=lambda sid: (
                self._streams[sid].descriptor.display_name
                or self._streams[sid].descriptor.stream_id
            ),
        )
        self.previewsChanged.emit()
        return state

    def _on_frame(self, frame: FrameEnvelope) -> None:
        descriptor = self._engine.bus.descriptor(frame.stream_id)
        if descriptor is None:
            return
        state = self._ensure_stream(descriptor)
        state.controller.push_frame(frame)
        state.frame_count += 1
        state.last_timestamp_ns = frame.timestamp_ns
        state.summary_text = (
            f"已接收 {state.frame_count} 帧 · 最近 "
            f"{format_timestamp_ns(frame.timestamp_ns)}"
        )
        state.dirty = True

    def _flush_previews(self) -> None:
        any_flushed = False
        for state in self._streams.values():
            if not state.dirty:
                continue
            state.dirty = False
            state.controller.flush()
            any_flushed = True

        if any_flushed:
            self.previewsChanged.emit()

    def _on_setting_changed(self, event: object) -> None:
        key = getattr(event, "key", None)
        if key == UI_PREVIEW_REFRESH_RATE_HZ_KEY:
            self._apply_refresh_rate()

    def _apply_refresh_rate(self) -> None:
        refresh_rate_hz = normalize_preview_refresh_rate_hz(
            self._settings.get(
                UI_PREVIEW_REFRESH_RATE_HZ_KEY,
                DEFAULT_PREVIEW_REFRESH_RATE_HZ,
            )
        )
        interval_ms = max(16, int(round(1000 / max(1, refresh_rate_hz))))
        self._refresh_timer.start(interval_ms)
