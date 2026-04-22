from __future__ import annotations

from collections.abc import Iterable

from PyQt6.QtWidgets import QVBoxLayout, QWidget

from modlink_sdk import FrameEnvelope, StreamDescriptor
from modlink_ui.bridge import QtSettingsBridge
from modlink_ui.widgets.shared import EmptyStateMessage

from .cards import DetachableStreamPreviewCard


class PreviewCardDeck(QWidget):
    """Shared card-container logic for live and replay preview panels."""

    def __init__(
        self,
        settings: QtSettingsBridge,
        *,
        empty_title: str,
        empty_description: str,
        hide_when_all_detached: bool,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self._settings = settings
        self._hide_when_all_detached = hide_when_all_detached
        self._cards: dict[str, DetachableStreamPreviewCard] = {}

        self.empty_state = EmptyStateMessage(empty_title, empty_description, self)
        self.cards_container = QWidget(self)
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(14)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.empty_state)
        layout.addWidget(self.cards_container)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._sync_container_visibility()

    def card(self, stream_id: str) -> DetachableStreamPreviewCard | None:
        return self._cards.get(stream_id)

    def push_frame_to_existing_card(self, frame: FrameEnvelope) -> bool:
        card = self.card(frame.stream_id)
        if card is None:
            return False
        card.push_frame(frame)
        return True

    def replace_cards(self, descriptors: Iterable[StreamDescriptor]) -> None:
        self.clear_cards()
        for descriptor in descriptors:
            self._add_card(descriptor)
        self._sync_container_visibility()

    def clear_cards(self) -> None:
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._cards.clear()

    def _add_card(self, descriptor: StreamDescriptor) -> None:
        card = DetachableStreamPreviewCard(
            descriptor,
            self._settings,
            self.cards_container,
        )
        card.sig_detached_changed.connect(self._on_card_detached_changed)
        self._cards[descriptor.stream_id] = card
        self.cards_layout.addWidget(card)

    def _on_card_detached_changed(self, _detached: bool) -> None:
        self._sync_container_visibility()

    def _sync_container_visibility(self) -> None:
        if not self.isVisible():
            self.empty_state.hide()
            self.cards_container.hide()
            return

        has_cards = bool(self._cards)
        self.empty_state.setVisible(not has_cards)
        self.cards_container.setVisible(has_cards and self._should_show_cards_container())

    def _should_show_cards_container(self) -> bool:
        if not self._hide_when_all_detached:
            return True
        return any(not card.is_detached for card in self._cards.values())
