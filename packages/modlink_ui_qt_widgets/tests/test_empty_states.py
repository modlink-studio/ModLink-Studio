from __future__ import annotations

import os
import shutil
import sys
import unittest
from pathlib import Path
from uuid import uuid4

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PACKAGE_ROOT.parents[1]
for path in (
    PACKAGE_ROOT,
    WORKSPACE_ROOT / "packages" / "modlink_sdk",
    WORKSPACE_ROOT / "packages" / "modlink_core",
    WORKSPACE_ROOT / "packages" / "modlink_qt_bridge",
):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication

from modlink_core.settings.service import SettingsService
from modlink_qt_bridge import QtSettingsBridge
from modlink_sdk import StreamDescriptor
from modlink_ui_qt_widgets.pages.device import DevicePage
from modlink_ui_qt_widgets.pages.main import MainPage
from modlink_ui_qt_widgets.widgets.main.preview import StreamPreviewPanel
from modlink_ui_qt_widgets.widgets.shared import EmptyStateMessage


class _BusStub(QObject):
    sig_frame = pyqtSignal(object)

    def __init__(self) -> None:
        super().__init__()
        self._descriptors: dict[str, StreamDescriptor] = {}

    def add_descriptor(self, descriptor: StreamDescriptor) -> None:
        self._descriptors[descriptor.stream_id] = descriptor

    def descriptor(self, stream_id: str) -> StreamDescriptor | None:
        return self._descriptors.get(stream_id)

    def descriptors(self) -> dict[str, StreamDescriptor]:
        return dict(self._descriptors)


class _AcquisitionStub(QObject):
    sig_state_changed = pyqtSignal(object)
    sig_error = pyqtSignal(str)
    sig_recording_failed = pyqtSignal(object)

    def __init__(self, root_dir: Path) -> None:
        super().__init__()
        self._root_dir = root_dir
        self._is_recording = False

    @property
    def root_dir(self) -> Path:
        return self._root_dir

    @property
    def is_recording(self) -> bool:
        return self._is_recording


class _EngineStub:
    def __init__(
        self,
        bus: _BusStub,
        settings: QtSettingsBridge,
        recording: _AcquisitionStub,
        driver_portals: tuple[object, ...] = (),
    ) -> None:
        self.bus = bus
        self.settings = settings
        self.recording = recording
        self._driver_portals = driver_portals

    def driver_portals(self) -> tuple[object, ...]:
        return self._driver_portals


class EmptyStateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        test_tmp_root = WORKSPACE_ROOT / ".tmp-tests"
        test_tmp_root.mkdir(exist_ok=True)
        self._temp_dir = test_tmp_root / f"empty-state-{uuid4().hex}"
        self._temp_dir.mkdir()
        self._settings = SettingsService(self._temp_dir / "empty-state-settings.json")
        self._settings_bridge = QtSettingsBridge(self._settings)

    def tearDown(self) -> None:
        shutil.rmtree(self._temp_dir, ignore_errors=True)

    @staticmethod
    def _descriptor() -> StreamDescriptor:
        return StreamDescriptor(
            device_id="test.01",
            modality="video",
            payload_type="video",
            nominal_sample_rate_hz=30.0,
            chunk_size=1,
            channel_names=("red", "green", "blue"),
            display_name="test preview",
        )

    def _engine(self, *, descriptors: tuple[StreamDescriptor, ...] = ()) -> _EngineStub:
        bus = _BusStub()
        for descriptor in descriptors:
            bus.add_descriptor(descriptor)
        acquisition = _AcquisitionStub(self._temp_dir)
        return _EngineStub(bus, self._settings_bridge, acquisition)

    def _pump_events(self) -> None:
        for _ in range(3):
            self._app.processEvents()

    def test_preview_panel_shows_empty_message_without_descriptors(self) -> None:
        panel = StreamPreviewPanel(self._engine())
        panel.show()
        self._pump_events()

        self.assertIsInstance(panel.empty_state, EmptyStateMessage)
        self.assertTrue(panel.empty_state.isVisible())
        self.assertFalse(panel.cards_container.isVisible())
        panel.close()

    def test_preview_panel_hides_empty_message_when_cards_exist(self) -> None:
        panel = StreamPreviewPanel(self._engine(descriptors=(self._descriptor(),)))
        panel.show()
        self._pump_events()

        self.assertFalse(panel.empty_state.isVisible())
        self.assertTrue(panel.cards_container.isVisible())
        self.assertEqual(len(panel._cards), 1)
        panel.close()

    def test_main_page_uses_preview_panel_empty_message(self) -> None:
        page = MainPage(self._engine())
        page.show()
        self._pump_events()

        self.assertFalse(hasattr(page, "empty_state_card"))
        self.assertIsInstance(page.preview_panel.empty_state, EmptyStateMessage)
        self.assertTrue(page.preview_panel.empty_state.isVisible())
        page.close()

    def test_device_page_uses_shared_empty_message(self) -> None:
        page = DevicePage(self._engine())
        page.show()
        self._pump_events()

        self.assertIsInstance(page.empty_state, EmptyStateMessage)
        self.assertTrue(page.empty_state.isVisible())
        self.assertEqual(page.empty_state.title_label.text(), "当前没有可用 driver")
        page.close()


if __name__ == "__main__":
    unittest.main()
