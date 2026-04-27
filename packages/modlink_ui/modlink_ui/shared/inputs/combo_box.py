from __future__ import annotations

from qfluentwidgets import ComboBox


def remove_combo_popup_outer_margin(combo_box: ComboBox) -> ComboBox:
    if getattr(combo_box, "_modlink_popup_margin_removed", False):
        return combo_box

    create_combo_menu = combo_box._createComboMenu

    def create_menu_without_outer_margin():
        menu = create_combo_menu()
        # QFluentWidgets leaves transparent margins for shadows; on Windows they show as an outer shell.
        menu.layout().setContentsMargins(0, 0, 0, 0)
        menu.adjustSize()
        return menu

    combo_box._createComboMenu = create_menu_without_outer_margin
    combo_box._modlink_popup_margin_removed = True
    return combo_box
