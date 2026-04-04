import QtQuick
import QtQuick.Controls

Rectangle {
    id: root

    property string text: ""
    property string tone: "neutral"

    UiTokens { id: ui }

    radius: height / 2
    implicitHeight: 26
    implicitWidth: label.implicitWidth + 22

    color: {
        if (tone === "success") return ui.successBg;
        if (tone === "info") return ui.infoBg;
        if (tone === "warning") return ui.warningBg;
        if (tone === "danger") return ui.dangerBg;
        return ui.surfaceAlt;
    }

    border.width: 1
    border.color: {
        if (tone === "success") return Qt.darker(ui.successBg, 1.08);
        if (tone === "info") return Qt.darker(ui.infoBg, 1.08);
        if (tone === "warning") return Qt.darker(ui.warningBg, 1.08);
        if (tone === "danger") return Qt.darker(ui.dangerBg, 1.08);
        return ui.borderSoft;
    }

    Label {
        id: label
        anchors.centerIn: parent
        text: root.text
        font.pixelSize: 12
        font.weight: Font.DemiBold
        color: {
            if (root.tone === "success") return ui.successFg;
            if (root.tone === "info") return ui.infoFg;
            if (root.tone === "warning") return ui.warningFg;
            if (root.tone === "danger") return ui.dangerFg;
            return ui.textSecondary;
        }
    }
}
