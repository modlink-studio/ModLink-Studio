from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from PyQt6.QtWidgets import QApplication
from qfluentwidgets import ComboBox

from modlink_ui.shared.inputs import remove_combo_popup_outer_margin


class ComboBoxPopupMarginTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def test_combo_popup_outer_margin_is_removed_on_created_menu(self) -> None:
        combo_box = ComboBox()
        remove_combo_popup_outer_margin(combo_box)

        menu = combo_box._createComboMenu()
        margins = menu.layout().contentsMargins()

        self.assertEqual(
            (margins.left(), margins.top(), margins.right(), margins.bottom()), (0, 0, 0, 0)
        )


if __name__ == "__main__":
    unittest.main()
