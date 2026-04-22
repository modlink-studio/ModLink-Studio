from __future__ import annotations

from PyQt6.QtWidgets import QWidget

from modlink_sdk import FrameEnvelope
from modlink_ui.bridge import QtModLinkBridge

from .card_deck import PreviewCardDeck


class StreamPreviewPanel(PreviewCardDeck):
    def __init__(
        self,
        engine: QtModLinkBridge,
        parent: QWidget | None = None,
    ) -> None:
        self.engine = engine
        self._descriptor_snapshot = self.engine.bus.descriptors()
        super().__init__(
            self.engine.settings,
            empty_title="当前还没有启动任何 driver",
            empty_description="启动 driver 后，实时预览会显示在这里。",
            hide_when_all_detached=True,
            parent=parent,
        )

        self.empty_state.setObjectName("stream-preview-empty-state")
        self.replace_cards(self._descriptor_snapshot.values())
        self.engine.bus.sig_frame.connect(self._on_frame)

    def _on_frame(self, frame: FrameEnvelope) -> None:
        if self.push_frame_to_existing_card(frame):
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
