import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root

    property string text: ""
    signal removeRequested()

    UiTokens { id: ui }

    radius: height / 2
    implicitHeight: 34
    implicitWidth: chipRow.implicitWidth + 18
    color: ui.surfaceAlt
    border.width: 1
    border.color: ui.borderSoft

    RowLayout {
        id: chipRow
        anchors.centerIn: parent
        spacing: 6

        Label {
            text: root.text
            font.pixelSize: 12
            font.weight: Font.Medium
            color: ui.textPrimary
        }

        ToolButton {
            text: "\u00d7"
            focusPolicy: Qt.NoFocus
            onClicked: root.removeRequested()
        }
    }
}
