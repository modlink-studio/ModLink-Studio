import QtQuick
import QtQuick.Controls

Rectangle {
    id: root

    property string text: ""
    signal removeRequested()

    radius: 999
    color: "#eef5fb"
    border.width: 1
    border.color: "#d7e3ef"
    implicitHeight: 34
    implicitWidth: label.implicitWidth + removeButton.implicitWidth + 24

    Row {
        anchors.centerIn: parent
        spacing: 6

        Text {
            id: label
            text: root.text
            color: "#24405a"
            font.pixelSize: 13
        }

        Button {
            id: removeButton
            text: "×"
            flat: true
            padding: 0
            onClicked: root.removeRequested()
            contentItem: Text {
                text: parent.text
                color: "#5f7288"
                font.pixelSize: 14
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
            background: Rectangle { color: "transparent" }
        }
    }
}
