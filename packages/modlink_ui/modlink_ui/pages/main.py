from __future__ import annotations

from PyQt6.QtCore import QEvent, QObject, QPoint, QTimer
from PyQt6.QtWidgets import QWidget

from modlink_core.runtime.engine import ModLinkEngine
from modlink_ui.widgets.main.acquisition import AcquisitionControlPanel
from modlink_ui.widgets.main.preview import StreamPreviewPanel
from modlink_ui.widgets.shared import BasePage


class MainPage(BasePage):
    """Realtime preview page for the ModLink Studio UI."""

    def __init__(self, engine: ModLinkEngine, parent: QWidget | None = None) -> None:
        super().__init__(
            page_key="main-page",
            title="实时展示",
            description="在这里直接查看实时流预览，底部悬浮控制采集。",
            parent=parent,
        )
        self.engine = engine
        self.acquisition_panel = AcquisitionControlPanel(engine, self)
        self.acquisition_panel.hide()
        self.preview_panel = StreamPreviewPanel(engine, self.scroll_widget)
        self.preview_panel.hide()
        self._bottom_spacer = QWidget(self.scroll_widget)
        self._bottom_spacer.setFixedHeight(0)

        self.content_layout.addWidget(self.preview_panel)
        self.content_layout.addWidget(self._bottom_spacer)
        self.content_layout.addStretch(1)
        self.acquisition_panel.raise_()

        self.scroll_area.viewport().installEventFilter(self)
        self.acquisition_panel.installEventFilter(self)
        QTimer.singleShot(0, self._sync_floating_acquisition_panel)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched in {self.scroll_area.viewport(), self.acquisition_panel} and event.type() in {
            QEvent.Type.Resize,
            QEvent.Type.Show,
            QEvent.Type.Hide,
            QEvent.Type.LayoutRequest,
        }:
            QTimer.singleShot(0, self._sync_floating_acquisition_panel)
        return super().eventFilter(watched, event)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._sync_floating_acquisition_panel()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        QTimer.singleShot(0, self._activate_floating_widgets)

    def _activate_floating_widgets(self) -> None:
        if not self.isVisible():
            return
        if not self.preview_panel.isVisible():
            self.preview_panel.show()
        self._sync_floating_acquisition_panel()

    def _sync_floating_acquisition_panel(self) -> None:
        viewport = self.scroll_area.viewport()
        if not viewport.isVisible():
            return

        panel_height = max(
            self.acquisition_panel.minimumSizeHint().height(),
            self.acquisition_panel.sizeHint().height(),
        )
        reserve_height = panel_height + 24
        if self._bottom_spacer.height() != reserve_height:
            self._bottom_spacer.setFixedHeight(reserve_height)

        viewport_top_left = viewport.mapTo(self, QPoint(0, 0))
        side_margin = 16
        bottom_margin = 12
        max_panel_width = 1160
        panel_width = min(
            max_panel_width,
            max(360, viewport.width() - side_margin * 2),
        )
        panel_x = viewport_top_left.x() + max(0, (viewport.width() - panel_width) // 2)
        panel_y = viewport_top_left.y() + viewport.height() - panel_height - bottom_margin

        self.acquisition_panel.setGeometry(
            panel_x,
            panel_y,
            panel_width,
            panel_height,
        )
        if not self.acquisition_panel.isVisible():
            self.acquisition_panel.show()
        self.acquisition_panel.raise_()
