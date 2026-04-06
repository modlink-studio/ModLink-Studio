from __future__ import annotations

from dataclasses import dataclass
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
    preview_item: "_PreviewItem"
    last_timestamp_ns: int | None = None
    dirty: bool = False
    hydrating: bool = False


class _PreviewItem(QObject):
    summaryTextChanged = pyqtSignal()
    frameCountChanged = pyqtSignal()

    def __init__(
        self,
        descriptor: StreamDescriptor,
        controller: StreamController,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._descriptor = descriptor
        self._controller = controller
        self._summary_text = "等待数据"
        self._frame_count = 0
        self.setObjectName(
            "streamPreviewCard_"
            + "".join(ch if ch.isalnum() else "_" for ch in descriptor.stream_id)
        )

    @pyqtProperty(str, constant=True)
    def streamId(self) -> str:
        return self._descriptor.stream_id

    @pyqtProperty(str, constant=True)
    def displayName(self) -> str:
        return self._descriptor.display_name or self._descriptor.stream_id

    @pyqtProperty(str, constant=True)
    def payloadType(self) -> str:
        return self._descriptor.payload_type

    @pyqtProperty(str, notify=summaryTextChanged)
    def summaryText(self) -> str:
        return self._summary_text

    @pyqtProperty(int, notify=frameCountChanged)
    def frameCount(self) -> int:
        return self._frame_count

    @pyqtProperty(str, constant=True)
    def channelSummary(self) -> str:
        return ", ".join(self._descriptor.channel_names) or "无 channel 标签"

    @pyqtProperty(str, constant=True)
    def sampleRateText(self) -> str:
        return f"{self._descriptor.nominal_sample_rate_hz:g} Hz"

    @pyqtProperty(QObject, constant=True)
    def controller(self) -> QObject:
        return self._controller

    def set_frame_status(self, frame_count: int, summary_text: str) -> None:
        if frame_count != self._frame_count:
            self._frame_count = frame_count
            self.frameCountChanged.emit()
        if summary_text != self._summary_text:
            self._summary_text = summary_text
            self.summaryTextChanged.emit()


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
    def previews(self) -> list[QObject]:
        result: list[QObject] = []
        for stream_id in self._stream_order:
            state = self._streams.get(stream_id)
            if state is not None:
                result.append(state.preview_item)
        return result

    def _ensure_stream(self, descriptor: StreamDescriptor) -> _StreamState:
        existing = self._streams.get(descriptor.stream_id)
        if existing is not None:
            return existing

        controller = create_stream_controller(descriptor, parent=self)
        preview_item = _PreviewItem(descriptor, controller, parent=self)
        state = _StreamState(
            descriptor=descriptor,
            controller=controller,
            preview_item=preview_item,
        )
        self._streams[descriptor.stream_id] = state
        controller.settingsChanged.connect(
            lambda stream_id=descriptor.stream_id: self._on_stream_settings_changed(
                stream_id
            )
        )

        state.hydrating = True
        settings = self._store.load(descriptor)
        apply_settings_to_controller(controller, settings)
        state.hydrating = False

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
        next_count = state.preview_item.frameCount + 1
        state.last_timestamp_ns = frame.timestamp_ns
        state.preview_item.set_frame_status(
            next_count,
            f"已接收 {next_count} 帧 · 最近 {format_timestamp_ns(frame.timestamp_ns)}",
        )
        state.dirty = True

    def _flush_previews(self) -> None:
        for state in self._streams.values():
            if not state.dirty:
                continue
            state.dirty = False
            state.controller.flush()

    def _on_stream_settings_changed(self, stream_id: str) -> None:
        state = self._streams.get(stream_id)
        if state is None or state.hydrating:
            return
        self._store.save(
            state.descriptor,
            state.controller.export_settings(),  # type: ignore[attr-defined]
        )

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
