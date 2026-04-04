from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from modlink_core import ModLinkEngine, SettingsService
from modlink_new_ui import create_application, load_window
from modlink_qt_bridge import QtModLinkBridge


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

        for obj in qml_engine.rootObjects():
            obj.deleteLater()
        bridge.shutdown()


if __name__ == "__main__":
    unittest.main()
