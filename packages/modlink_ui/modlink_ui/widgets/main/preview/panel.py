from __future__ import annotations

from PyQt6.QtWidgets import QVBoxLayout, QWidget

from modlink_core.runtime.engine import ModLinkEngine
from modlink_sdk import FrameEnvelope, StreamDescriptor

from .cards import DetachableStreamPreviewCard


class StreamPreviewPanel(QWidget):
    def __init__(
        self,
        engine: ModLinkEngine,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self.engine = engine
        self._cards: dict[str, DetachableStreamPreviewCard] = {}

        self.cards_container = QWidget(self)
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(14)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.cards_container)

        for descriptor in self.engine.bus.descriptors().values():
            card = DetachableStreamPreviewCard(descriptor, self.cards_container)
            card.sig_detached_changed.connect(self._on_card_detached_changed)
            self._cards[descriptor.stream_id] = card
            self.cards_layout.addWidget(card)

        self.engine.bus.sig_frame.connect(self._on_frame)
        self._sync_container_visibility()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._sync_container_visibility()

    def _on_frame(self, frame: FrameEnvelope) -> None:
        card = self._cards.get(frame.stream_id)
        if card is None:
            raise RuntimeError(
                "PREVIEW_DESCRIPTOR_MISMATCH: "
                f"received frame for stream_id={frame.stream_id}, "
                "but StreamPreviewPanel did not initialize a matching preview card"
            )
        card.push_frame(frame)

    def _on_card_detached_changed(self, _detached: bool) -> None:
        self._sync_container_visibility()

    def _sync_container_visibility(self) -> None:
        if not self.isVisible():
            self.cards_container.hide()
            return
        self.cards_container.setVisible(any(not card.is_detached for card in self._cards.values()))
