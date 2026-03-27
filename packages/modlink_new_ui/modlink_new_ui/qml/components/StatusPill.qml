import QtQuick

Rectangle {
    id: root

    property string text: ""
    property string tone: "neutral"

    radius: 999
    implicitHeight: 28
    implicitWidth: label.implicitWidth + 24

    color: tone === "success" ? "#dff7e8"
        : tone === "info" ? "#e0efff"
        : tone === "warning" ? "#fff2cf"
        : "#eef3f7"

    border.width: 1
    border.color: tone === "success" ? "#9ed7b3"
        : tone === "info" ? "#a7c8ee"
        : tone === "warning" ? "#e5c677"
        : "#d1dbe5"

    Text {
        id: label
        anchors.centerIn: parent
        text: root.text
        font.pixelSize: 13
        font.weight: Font.DemiBold
        color: tone === "success" ? "#14532d"
            : tone === "info" ? "#0f5cab"
            : tone === "warning" ? "#7c5a00"
            : "#445769"
    }
}
