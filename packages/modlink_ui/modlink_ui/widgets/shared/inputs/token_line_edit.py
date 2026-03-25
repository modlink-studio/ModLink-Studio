from __future__ import annotations

import re
from collections.abc import Callable

from PyQt6.QtCore import QEvent, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QFontMetrics, QKeyEvent, QMouseEvent, QPainter, QPainterPath
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLineEdit, QSizePolicy, QWidget
from qfluentwidgets import (
    CaptionLabel,
    FluentIcon as FIF,
    LineEdit,
    TransparentToolButton,
    isDarkTheme,
    setFont,
)
from qfluentwidgets.components.layout import FlowLayout


class _TokenChip(QFrame):
    sig_remove_requested = pyqtSignal(str)

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.text = text
        self.setObjectName("token-line-edit-chip")

        self.label = CaptionLabel(text, self)
        setFont(self.label, 12)
        self.remove_button = TransparentToolButton(FIF.CLOSE, self)
        self.remove_button.setToolTip("删除")
        self.remove_button.setFixedSize(16, 16)
        self.remove_button.setIconSize(QSize(8, 8))
        self.remove_button.clicked.connect(self._request_remove)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 1, 1, 1)
        layout.setSpacing(1)
        layout.addWidget(self.label)
        layout.addWidget(self.remove_button)

        self._apply_styles()

    def _request_remove(self) -> None:
        self.sig_remove_requested.emit(self.text)

    def _apply_styles(self) -> None:
        border = (
            "rgba(255, 255, 255, 0.14)"
            if isDarkTheme()
            else "rgba(15, 23, 42, 0.08)"
        )
        background = (
            "rgba(255, 255, 255, 0.05)"
            if isDarkTheme()
            else "rgba(15, 23, 42, 0.03)"
        )
        self.setStyleSheet(
            "QFrame#token-line-edit-chip {"
            f"border: 1px solid {border};"
            f"background: {background};"
            "border-radius: 8px;"
            "}"
        )

    def refresh_style(self) -> None:
        self._apply_styles()


class _TokenLineEditShell(LineEdit):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self._visual_focus = False
        self.setReadOnly(True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.setClearButtonEnabled(False)
        self.setText("")
        self.setMinimumHeight(33)
        self.setMaximumHeight(16777215)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def set_visual_focus(self, focused: bool) -> None:
        if self._visual_focus == focused:
            return
        self._visual_focus = focused
        self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if not self._visual_focus:
            return

        painter = QPainter(self)
        painter.setRenderHints(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)

        path = QPainterPath()
        width = self.width()
        height = self.height()
        path.addRoundedRect(0, height - 10, width, 10, 5, 5)

        rect_path = QPainterPath()
        rect_path.addRect(0, height - 10, width, 8)
        painter.fillPath(path.subtracted(rect_path), self.focusedBorderColor())


class TokenLineEdit(QWidget):
    sig_tokens_changed = pyqtSignal(object)

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        placeholder_text: str = "",
        max_tokens: int | None = None,
        token_normalizer: Callable[[str], str | None] | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self._tokens: list[str] = []
        self._chips: dict[str, _TokenChip] = {}
        self._max_tokens = max_tokens
        self._token_normalizer = token_normalizer or self._default_normalizer
        self._placeholder_text = placeholder_text

        self.setObjectName("token-line-edit")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.setMinimumHeight(33)

        self.shell = _TokenLineEditShell(self)
        self.shell.setEnabled(self.isEnabled())
        self.shell.lower()

        self.flow_layout = FlowLayout(self)
        self.flow_layout.setContentsMargins(10, 6, 10, 6)
        self.flow_layout.setHorizontalSpacing(4)
        self.flow_layout.setVerticalSpacing(4)

        self.input_edit = QLineEdit(self)
        self.input_edit.setPlaceholderText(placeholder_text)
        self.input_edit.setFrame(False)
        self.input_edit.setMinimumWidth(88)
        self.input_edit.setMaximumWidth(220)
        self.input_edit.setSizePolicy(
            QSizePolicy.Policy.MinimumExpanding,
            QSizePolicy.Policy.Fixed,
        )
        self.input_edit.setFont(self.shell.font())
        self.input_edit.installEventFilter(self)
        self.input_edit.textChanged.connect(self._update_input_width)
        self.input_edit.editingFinished.connect(self._commit_pending_input)
        self.flow_layout.addWidget(self.input_edit)

        self.input_edit.setStyleSheet(
            "QLineEdit {"
            "background: transparent;"
            "border: none;"
            "padding: 0px;"
            "}"
        )
        self._sync_placeholder_text()
        self._update_input_width()

    def tokens(self) -> list[str]:
        return list(self._tokens)

    def set_tokens(self, tokens: list[str]) -> None:
        self.clear_tokens()
        for token in tokens:
            self.add_token(token)

    def clear_tokens(self) -> None:
        for token in list(self._tokens):
            self.remove_token(token)

    def add_token(self, token: str) -> bool:
        normalized = self._token_normalizer(token)
        if not normalized:
            return False
        if normalized in self._chips:
            return False
        if self._max_tokens is not None and len(self._tokens) >= self._max_tokens:
            return False

        chip = _TokenChip(normalized, self)
        chip.sig_remove_requested.connect(self.remove_token)
        self._tokens.append(normalized)
        self._chips[normalized] = chip
        self.flow_layout.insertWidget(max(0, self.flow_layout.count() - 1), chip)
        self._emit_tokens_changed()
        self._sync_placeholder_text()
        self._update_input_width()
        self._refresh_layout()
        return True

    def remove_token(self, token: str) -> None:
        chip = self._chips.pop(token, None)
        if chip is None:
            return
        self._tokens.remove(token)
        self.flow_layout.removeWidget(chip)
        chip.deleteLater()
        self._emit_tokens_changed()
        self._sync_placeholder_text()
        self._update_input_width()
        self._refresh_layout()

    def eventFilter(self, obj: object, event: QEvent) -> bool:
        if obj is self.input_edit:
            if event.type() == QEvent.Type.FocusIn:
                self.shell.set_visual_focus(True)
            elif event.type() == QEvent.Type.FocusOut:
                self.shell.set_visual_focus(False)
            elif event.type() == QEvent.Type.KeyPress:
                key_event = event
                if isinstance(key_event, QKeyEvent):
                    if key_event.key() in {Qt.Key.Key_Return, Qt.Key.Key_Enter}:
                        self._commit_pending_input()
                        return True
                    if key_event.text() in {",", "，", ";", "；"}:
                        self._commit_pending_input()
                        return True
                    if (
                        key_event.key() == Qt.Key.Key_Backspace
                        and not self.input_edit.text()
                        and self._tokens
                    ):
                        self.remove_token(self._tokens[-1])
                        return True
        return super().eventFilter(obj, event)

    def changeEvent(self, event: QEvent) -> None:
        super().changeEvent(event)
        if event.type() in {QEvent.Type.EnabledChange, QEvent.Type.PaletteChange}:
            self.shell.setEnabled(self.isEnabled())
            for chip in self._chips.values():
                chip.refresh_style()
            self.shell.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        super().mousePressEvent(event)
        self.input_edit.setFocus()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.shell.setGeometry(self.rect())

    def _commit_pending_input(self) -> None:
        text = self.input_edit.text().strip()
        if not text:
            return
        for part in re.split(r"[,，;；\s]+", text):
            if part:
                self.add_token(part)
        self.input_edit.clear()
        self._sync_placeholder_text()
        self._update_input_width()
        self._refresh_layout()

    def _update_input_width(self) -> None:
        metrics = QFontMetrics(self.input_edit.font())
        text = self.input_edit.text().strip()
        if not text and self._tokens:
            self.input_edit.setFixedWidth(24)
            return

        text = text or self.input_edit.placeholderText() or "88"
        width = metrics.horizontalAdvance(text + "  ")
        self.input_edit.setFixedWidth(max(88, min(220, width)))

    def _emit_tokens_changed(self) -> None:
        self.sig_tokens_changed.emit(self.tokens())

    def _sync_placeholder_text(self) -> None:
        if self._tokens:
            self.input_edit.setPlaceholderText("")
        else:
            self.input_edit.setPlaceholderText(self._placeholder_text)

    def _refresh_layout(self) -> None:
        self.updateGeometry()
        self.flow_layout.invalidate()
        self.flow_layout.setGeometry(self.rect())

    @staticmethod
    def _default_normalizer(token: str) -> str | None:
        normalized = token.strip()
        return normalized or None
