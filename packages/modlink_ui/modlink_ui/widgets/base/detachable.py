from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget
from qfluentwidgets import FluentIcon as FIF, TransparentToolButton


class _DetachedWindow(QWidget):
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

    def showEvent(self, event) -> None:
        super().showEvent(event)
        container = self.content_container
        if container.layout() is None or container.layout().count() == 0:
            return
        item = container.layout().itemAt(0)
        widget = item.widget() if item is not None else None
        if isinstance(widget, QWidget) and not widget.isVisible():
            widget.show()


class DetachableWidgetHost(QWidget):
    sig_detached_changed = pyqtSignal(bool)

    def __init__(
        self,
        *,
        window_title: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self._content_widget: QWidget | None = None
        self._toggle_buttons: list[TransparentToolButton] = []
        self._detached_window = _DetachedWindow(window_title)
        self._detached_window.sig_close_requested.connect(self.attach_content)
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

    @property
    def is_detached(self) -> bool:
        return self._content_widget is not None and self._content_widget.parent() is self._detached_window.content_container

    def set_content_widget(self, widget: QWidget) -> None:
        self._content_widget = widget
        self._mount_embedded()
        self._sync_state()

    def create_toggle_button(self, parent: QWidget | None = None) -> TransparentToolButton:
        button = TransparentToolButton(FIF.FULL_SCREEN, parent)
        button.clicked.connect(self.toggle_detached)
        self._toggle_buttons.append(button)
        self._sync_toggle_button(button)
        return button

    def toggle_detached(self) -> None:
        if self.is_detached:
            self.attach_content()
        else:
            self.detach_content()

    def detach_content(self) -> None:
        if self._content_widget is None or self.is_detached:
            return

        size = self._content_widget.size()
        self._mount_detached()
        self._detached_window.resize(max(960, size.width()), max(640, size.height()))
        self._detached_window.show()
        self._detached_window.raise_()
        self._detached_window.activateWindow()
        self._sync_state()

    def attach_content(self) -> None:
        if self._content_widget is None or not self.is_detached:
            return

        self._mount_embedded()
        self._detached_window.hide()
        self._sync_state()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.is_detached:
            self.attach_content()
        super().closeEvent(event)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._content_widget is not None and not self.is_detached and not self._content_widget.isVisible():
            self._content_widget.show()

    def _mount_embedded(self) -> None:
        if self._content_widget is None:
            return
        self._content_widget.setParent(self._embedded_container)
        self._embedded_layout.addWidget(self._content_widget)
        if self.isVisible():
            self._content_widget.show()

    def _mount_detached(self) -> None:
        if self._content_widget is None:
            return
        self._content_widget.setParent(self._detached_window.content_container)
        self._detached_window.content_layout.addWidget(self._content_widget)
        if self._detached_window.isVisible():
            self._content_widget.show()

    def _sync_state(self) -> None:
        is_attached = not self.is_detached
        self._embedded_container.setVisible(is_attached)
        self.setVisible(is_attached)
        self.updateGeometry()
        for button in self._toggle_buttons:
            self._sync_toggle_button(button)
        self.sig_detached_changed.emit(self.is_detached)

    def _sync_toggle_button(self, button: TransparentToolButton) -> None:
        button.setIcon(FIF.BACK_TO_WINDOW if self.is_detached else FIF.FULL_SCREEN)
        button.setToolTip("")
