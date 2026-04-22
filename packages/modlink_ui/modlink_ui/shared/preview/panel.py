from __future__ import annotations

from PyQt6.QtWidgets import QVBoxLayout, QWidget

from modlink_sdk import FrameEnvelope, StreamDescriptor
from modlink_ui.bridge import QtModLinkBridge
from modlink_ui.shared import EmptyStateMessage

from .cards import DetachableStreamPreviewCard


class StreamPreviewPanel(QWidget):
    def __init__(
        self,
        engine: QtModLinkBridge,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self.engine = engine
        self._cards: dict[str, DetachableStreamPreviewCard] = {}
        self._descriptor_snapshot = self.engine.bus.descriptors()
        self.empty_state = EmptyStateMessage(
            "当前还没有启动任何 driver",
            "启动 driver 后，实时预览会显示在这里。",
            self,
        )

        self.empty_state.setObjectName("stream-preview-empty-state")
        self.cards_container = QWidget(self)
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(14)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.empty_state)
        layout.addWidget(self.cards_container)

        for descriptor in self._descriptor_snapshot.values():
            self._add_card(descriptor)

        self.engine.bus.sig_frame.connect(self._on_frame)
        self._sync_container_visibility()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._sync_container_visibility()

    def _on_frame(self, frame: FrameEnvelope) -> None:
        card = self._cards.get(frame.stream_id)
        if card is not None:
            card.push_frame(frame)
            return

        descriptor = self.engine.bus.descriptor(frame.stream_id)
        if descriptor is not None:
            raise RuntimeError(
                "PREVIEW_STREAM_SNAPSHOT_VIOLATION: "
                f"received frame for stream_id={frame.stream_id}, "
                "but StreamPreviewPanel only supports descriptors present when the page "
                "was initialized. Rebuild the preview panel to include runtime-added streams."
            )

        raise RuntimeError(
            "PREVIEW_UNKNOWN_STREAM: "
            f"received frame for stream_id={frame.stream_id}, "
            "but the stream bus does not have a matching descriptor."
        )

    def _on_card_detached_changed(self, _detached: bool) -> None:
        self._sync_container_visibility()

    def _add_card(self, descriptor: StreamDescriptor) -> None:
        card = DetachableStreamPreviewCard(
            descriptor,
            self.engine.settings,
            self.cards_container,
        )
        card.sig_detached_changed.connect(self._on_card_detached_changed)
        self._cards[descriptor.stream_id] = card
        self.cards_layout.addWidget(card)

    def _sync_container_visibility(self) -> None:
        if not self.isVisible():
            self.empty_state.hide()
            self.cards_container.hide()
            return

        has_cards = bool(self._cards)
        self.empty_state.setVisible(not has_cards)
        self.cards_container.setVisible(
            has_cards and any(not card.is_detached for card in self._cards.values())
        )
