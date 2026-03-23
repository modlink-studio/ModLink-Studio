from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import CaptionLabel, SimpleCardWidget, StrongBodyLabel

from modlink_core.runtime.engine import ModLinkEngine
from modlink_sdk import FrameEnvelope, StreamDescriptor

from ..base import DetachableWidgetHost
from .views import create_stream_view


class StreamPreviewCard(SimpleCardWidget):
    def __init__(
        self,
        descriptor: StreamDescriptor,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self.descriptor = descriptor
        self.setBorderRadius(12)
        self.setToolTip(descriptor.stream_id)

        title = descriptor.display_name or descriptor.stream_id

        self.title_label = StrongBodyLabel(title, self)
        self.stream_view = create_stream_view(descriptor, self)
        self.summary_label = CaptionLabel(self._summary_text(), self)
        self.header_action_layout = QHBoxLayout()
        self.header_action_layout.setContentsMargins(0, 0, 0, 0)
        self.header_action_layout.setSpacing(4)
        self.header_action_layout.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight
        )

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)
        header_layout.addWidget(self.title_label, 1)
        header_layout.addLayout(self.header_action_layout)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(8)
        layout.addLayout(header_layout)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.stream_view, 1)

    def push_frame(self, frame: FrameEnvelope) -> None:
        self.stream_view.push_frame(frame)
        self.summary_label.setText(self._summary_text())

    def _summary_text(self) -> str:
        descriptor = self.descriptor
        sample_rate = float(descriptor.nominal_sample_rate_hz or 0.0)
        channel_count = len(descriptor.channel_names)
        parts = [
            descriptor.payload_type,
            descriptor.modality,
            f"{channel_count} ch",
            f"{sample_rate:.1f} Hz",
        ]
        if descriptor.unit:
            parts.append(descriptor.unit)
        parts.append("正在更新" if self.stream_view.has_frame else "等待首帧")
        return " · ".join(parts)

    @property
    def has_frame(self) -> bool:
        return self.stream_view.has_frame

    def add_header_action(self, widget: QWidget) -> None:
        widget.setParent(self)
        self.header_action_layout.addWidget(widget)


class DetachableStreamPreviewCard(DetachableWidgetHost):
    def __init__(
        self,
        descriptor: StreamDescriptor,
        parent: QWidget | None = None,
    ) -> None:
        title = descriptor.display_name or descriptor.stream_id
        super().__init__(
            window_title=title,
            parent=parent,
        )
        self.descriptor = descriptor
        self.card = StreamPreviewCard(descriptor)
        self.popout_button = self.create_toggle_button()
        self.card.add_header_action(self.popout_button)
        self.set_content_widget(self.card)

    def push_frame(self, frame: FrameEnvelope) -> None:
        self.card.push_frame(frame)

    @property
    def has_frame(self) -> bool:
        return self.card.has_frame


class StreamPreviewPanel(QWidget):
    def __init__(
        self,
        engine: ModLinkEngine,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self.engine = engine
        self._descriptors: dict[str, StreamDescriptor] = {}
        self._cards: dict[str, DetachableStreamPreviewCard] = {}
        self.empty_label = CaptionLabel("连接设备并启动流后会自动出现预览。", self)
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.cards_container = QWidget(self)
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(14)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.cards_container)
        layout.addWidget(self.empty_label)

        for descriptor in self.engine.bus.descriptors().values():
            self._descriptors[descriptor.stream_id] = descriptor

        self.engine.bus.sig_stream_descriptor.connect(self._on_stream_descriptor)
        self.engine.bus.sig_frame.connect(self._on_frame)
        self._refresh_empty_state()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._materialize_pending_cards()
        self._refresh_empty_state()

    def _on_stream_descriptor(self, descriptor: object) -> None:
        if not isinstance(descriptor, StreamDescriptor):
            return
        self._descriptors[descriptor.stream_id] = descriptor
        if self.isVisible():
            self._ensure_card(descriptor)
        self._refresh_empty_state()

    def _on_frame(self, frame: FrameEnvelope) -> None:
        card = self._cards.get(frame.stream_id)
        if card is None:
            descriptor = self._descriptors.get(frame.stream_id)
            if descriptor is None:
                descriptor = self.engine.bus.descriptor(frame.stream_id)
            if descriptor is None:
                return
            self._descriptors[descriptor.stream_id] = descriptor
            card = self._ensure_card(descriptor)
        card.push_frame(frame)

    def _materialize_pending_cards(self) -> None:
        for descriptor in self._descriptors.values():
            self._ensure_card(descriptor)

    def _ensure_card(self, descriptor: StreamDescriptor) -> DetachableStreamPreviewCard:
        existing = self._cards.get(descriptor.stream_id)
        if existing is not None:
            return existing

        card = DetachableStreamPreviewCard(descriptor, self.cards_container)
        card.sig_detached_changed.connect(lambda _detached, self=self: self._refresh_empty_state())
        self._cards[descriptor.stream_id] = card
        self.cards_layout.addWidget(card)
        self._refresh_empty_state()
        return card

    def _refresh_empty_state(self) -> None:
        has_cards = bool(self._descriptors)
        has_embedded_cards = any(not card.is_detached for card in self._cards.values())
        self.cards_container.setVisible(has_embedded_cards)
        self.empty_label.setVisible(not has_cards)
        self._sync_card_visibility()

    def _sync_card_visibility(self) -> None:
        panel_visible = self.isVisible()
        for card in self._cards.values():
            should_show = panel_visible and not card.is_detached
            if should_show:
                card.show()
            else:
                card.hide()
