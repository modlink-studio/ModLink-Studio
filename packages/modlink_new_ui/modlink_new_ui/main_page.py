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
from .helpers import (
    downsample_series,
    format_timestamp_ns,
    frame_to_qimage,
    qimage_to_data_url,
)


@dataclass(slots=True)
class _PreviewState:
    descriptor: StreamDescriptor
    frame_count: int = 0
    last_timestamp_ns: int | None = None
    plot_points: list[float] = field(default_factory=list)
    image_data_url: str = ""
    summary_text: str = "等待数据"
    pending_frame: FrameEnvelope | None = None


class MainPageController(QObject):
    previewsChanged = pyqtSignal()
    messageRaised = pyqtSignal(str)

    def __init__(self, engine: QtModLinkBridge, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._engine = engine
        self._settings = engine.settings
        self._acquisition = AcquisitionController(engine, parent=self)
        self._previews: dict[str, _PreviewState] = {}
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._flush_previews)
        self._apply_refresh_rate()

        self._acquisition.messageRaised.connect(self.messageRaised.emit)
        self._engine.bus.sig_frame.connect(self._on_frame)
        self._settings.sig_setting_changed.connect(self._on_setting_changed)

        for descriptor in self._engine.bus.descriptors().values():
            self._ensure_preview_state(descriptor)

    @pyqtProperty(QObject, constant=True)
    def acquisition(self) -> QObject:
        return self._acquisition

    @pyqtProperty("QVariantList", notify=previewsChanged)
    def previews(self) -> list[dict[str, object]]:
        ordered = sorted(
            self._previews.values(),
            key=lambda item: item.descriptor.display_name or item.descriptor.stream_id,
        )
        return [
            {
                "streamId": state.descriptor.stream_id,
                "displayName": state.descriptor.display_name
                or state.descriptor.stream_id,
                "payloadType": state.descriptor.payload_type,
                "summaryText": state.summary_text,
                "frameCount": state.frame_count,
                "plotPoints": state.plot_points,
                "imageDataUrl": state.image_data_url,
                "channelSummary": ", ".join(state.descriptor.channel_names)
                or "无 channel 标签",
                "sampleRateText": f"{state.descriptor.nominal_sample_rate_hz:g} Hz",
            }
            for state in ordered
        ]

    def _ensure_preview_state(self, descriptor: StreamDescriptor) -> _PreviewState:
        existing = self._previews.get(descriptor.stream_id)
        if existing is not None:
            return existing
        state = _PreviewState(descriptor=descriptor)
        self._previews[descriptor.stream_id] = state
        self.previewsChanged.emit()
        return state

    def _on_frame(self, frame: FrameEnvelope) -> None:
        descriptor = self._engine.bus.descriptor(frame.stream_id)
        if descriptor is None:
            return
        state = self._ensure_preview_state(descriptor)
        state.pending_frame = frame

    def _flush_previews(self) -> None:
        dirty = False
        for state in self._previews.values():
            frame = state.pending_frame
            if frame is None:
                continue

            state.pending_frame = None
            state.frame_count += 1
            state.last_timestamp_ns = frame.timestamp_ns
            state.summary_text = (
                f"已接收 {state.frame_count} 帧 · 最近 "
                f"{format_timestamp_ns(frame.timestamp_ns)}"
            )
            if state.descriptor.payload_type == "signal":
                payload = np.asarray(frame.data)
                if payload.ndim == 1:
                    series = payload
                elif payload.ndim >= 2:
                    series = payload[0]
                else:
                    series = np.asarray([], dtype=np.float32)
                state.plot_points = downsample_series(series)
                state.image_data_url = ""
            else:
                image = frame_to_qimage(frame, state.descriptor)
                state.image_data_url = qimage_to_data_url(image)
                state.plot_points = []
            dirty = True

        if dirty:
            self.previewsChanged.emit()

    def _on_setting_changed(self, event: object) -> None:
        if getattr(event, "key", None) != UI_PREVIEW_REFRESH_RATE_HZ_KEY:
            return
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
