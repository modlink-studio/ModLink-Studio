import QtQuick
import QtQuick.Controls

Rectangle {
    id: root

    property string text: ""
    signal removeRequested()

    radius: 12
    color: Qt.rgba(palette.highlight.r, palette.highlight.g, palette.highlight.b, 0.08)
    border.width: 1
    border.color: Qt.rgba(palette.highlight.r, palette.highlight.g, palette.highlight.b, 0.2)
    implicitHeight: 30
    implicitWidth: label.implicitWidth + removeBtn.implicitWidth + 20

    Row {
        anchors.centerIn: parent
        spacing: 4

        Text {
            id: label
            text: root.text
            color: palette.windowText
            font.pixelSize: 12
            anchors.verticalCenter: parent.verticalCenter
        }

        Button {
            id: removeBtn
            text: "\u00d7"
            flat: true
            padding: 0
            implicitWidth: 20
            implicitHeight: 20
            onClicked: root.removeRequested()
            anchors.verticalCenter: parent.verticalCenter
            contentItem: Text {
                text: parent.text
                color: palette.placeholderText
                font.pixelSize: 14
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
            background: Rectangle { color: "transparent" }
        }
    }
}
