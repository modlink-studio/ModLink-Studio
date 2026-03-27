import QtQuick
import QtQuick.Controls

Button {
    id: root

    property bool active: false

    implicitHeight: 44
    implicitWidth: 180

    background: Rectangle {
        radius: 14
        color: root.active
            ? "#d7ebff"
            : (root.hovered ? "#eef5fb" : "transparent")
    }

    contentItem: Text {
        text: root.text
        color: root.active ? "#0f5cab" : "#203344"
        font.pixelSize: 15
        font.weight: root.active ? Font.DemiBold : Font.Medium
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }
}
