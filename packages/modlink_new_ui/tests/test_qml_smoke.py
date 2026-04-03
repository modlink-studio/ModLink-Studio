from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Fusion")

from modlink_core import ModLinkEngine, SettingsService
from modlink_qt_bridge import QtModLinkBridge
from modlink_new_ui import create_application, load_window


class QmlSmokeTest(unittest.TestCase):
    def test_qml_window_loads(self) -> None:
        app = create_application([])
        settings = SettingsService(parent=app)
        runtime = ModLinkEngine(settings=settings, parent=app)
        bridge = QtModLinkBridge(runtime, parent=app)
        qml_engine, controller = load_window(bridge, parent=app)
        app.processEvents()

        self.assertTrue(qml_engine.rootObjects())
        self.assertIsNotNone(controller.mainPage)
        self.assertIsNotNone(controller.devicePage)
        self.assertIsNotNone(controller.settingsPage)

        for obj in qml_engine.rootObjects():
            obj.deleteLater()
        bridge.shutdown()

    def test_gpu_items_importable(self) -> None:
        from modlink_new_ui.gpu import WaveformItem, TextureItem
        self.assertIsNotNone(WaveformItem)
        self.assertIsNotNone(TextureItem)

    def test_preview_controllers_importable(self) -> None:
        from modlink_new_ui.preview.stream_controller_factory import create_stream_controller
        self.assertIsNotNone(create_stream_controller)


if __name__ == "__main__":
    unittest.main()
