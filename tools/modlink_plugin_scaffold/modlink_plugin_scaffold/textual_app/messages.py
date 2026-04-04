"""Custom Textual messages for scaffold app widgets."""

from __future__ import annotations

from textual.message import Message

from .state import PreviewTab


class StreamSelected(Message):
    def __init__(self, index: int) -> None:
        self.index = index
        super().__init__()


class StreamActionRequested(Message):
    def __init__(self, action: str) -> None:
        self.action = action
        super().__init__()


class PreviewTabRequested(Message):
    def __init__(self, tab: PreviewTab) -> None:
        self.tab = tab
        super().__init__()
