from __future__ import annotations

from PyQt6.QtCore import QSize
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget
from qfluentwidgets import FluentIcon as FIF, TransparentToolButton

from modlink_qt_bridge import QtSettingsBridge
from modlink_sdk import FrameEnvelope, StreamDescriptor

from .stream import StreamPreviewCard


class _DetachedPreviewWindow(QWidget):
    sig_close_requested = pyqtSignal()

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent, flags=Qt.WindowType.Window)
        self.setWindowTitle(title)

        self.content_container = QWidget(self)
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.content_container)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.sig_close_requested.emit()
        event.ignore()


class DetachableStreamPreviewCard(QWidget):
    sig_detached_changed = pyqtSignal(bool)

    def __init__(
        self,
        descriptor: StreamDescriptor,
        settings: QtSettingsBridge,
        parent: QWidget | None = None,
    ) -> None:
        title = descriptor.display_name or descriptor.stream_id
        super().__init__(parent=parent)
        self.descriptor = descriptor
        self._is_detached = False
        self._detached_size: QSize | None = None
        self._detached_window = _DetachedPreviewWindow(title)
        self._detached_window.sig_close_requested.connect(
            lambda: self._set_detached(False)
        )
        self.destroyed.connect(self._detached_window.deleteLater)

        self._embedded_container = QWidget(self)
        self._embedded_layout = QVBoxLayout(self._embedded_container)
        self._embedded_layout.setContentsMargins(0, 0, 0, 0)
        self._embedded_layout.setSpacing(0)
        self._embedded_container.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Minimum,
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._embedded_container)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.card = StreamPreviewCard(descriptor, settings)
        self.popout_button = TransparentToolButton(FIF.FULL_SCREEN, self.card)
        self.popout_button.clicked.connect(
            lambda: self._set_detached(not self._is_detached)
        )
        self.card.add_header_action(self.popout_button)
        self._move_content(self._embedded_container, self._embedded_layout)

    def push_frame(self, frame: FrameEnvelope) -> None:
        self.card.push_frame(frame)

    @property
    def has_frame(self) -> bool:
        return self.card.has_frame

    @property
    def is_detached(self) -> bool:
        return self._is_detached

    def detach_content(self) -> None:
        self._set_detached(True)

    def attach_content(self) -> None:
        self._set_detached(False)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._is_detached:
            self._set_detached(False)
        super().closeEvent(event)

    def _move_content(self, container: QWidget, layout: QVBoxLayout) -> None:
        self.card.setParent(container)
        layout.addWidget(self.card)
        self.card.show()

    def _set_detached(self, detached: bool) -> None:
        if detached == self._is_detached:
            return

        self._set_stream_view_embedded_mode(not detached)
        if detached:
            size = self._detached_size or self.card.size()
            if size.width() <= 0 or size.height() <= 0:
                size = self.card.sizeHint()
            self._move_content(
                self._detached_window.content_container,
                self._detached_window.content_layout,
            )
            self._detached_window.resize(
                max(960, size.width()),
                max(640, size.height()),
            )
            self._detached_window.show()
            self._detached_window.raise_()
            self._detached_window.activateWindow()
        else:
            self._detached_size = self._detached_window.size()
            self._move_content(self._embedded_container, self._embedded_layout)
            self._detached_window.hide()

        self._is_detached = detached
        self._embedded_container.setVisible(not detached)
        self.setVisible(not detached)
        self.updateGeometry()
        self.card.updateGeometry()
        self.popout_button.setIcon(
            FIF.BACK_TO_WINDOW if self._is_detached else FIF.FULL_SCREEN
        )
        self.sig_detached_changed.emit(detached)

    def _set_stream_view_embedded_mode(self, embedded: bool) -> None:
        setter = getattr(self.card.stream_view, "set_embedded_mode", None)
        if callable(setter):
            setter(embedded)
