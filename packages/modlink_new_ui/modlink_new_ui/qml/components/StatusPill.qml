import QtQuick

Rectangle {
    id: root

    property string text: ""
    property string tone: "neutral"

    radius: 12
    implicitHeight: 24
    implicitWidth: label.implicitWidth + 20

    color: {
        if (tone === "success") return Qt.rgba(0.0, 0.6, 0.3, 0.12);
        if (tone === "info")    return Qt.rgba(0.0, 0.4, 0.8, 0.12);
        if (tone === "warning") return Qt.rgba(0.8, 0.6, 0.0, 0.12);
        return Qt.rgba(0.5, 0.5, 0.5, 0.08);
    }

    border.width: 1
    border.color: {
        if (tone === "success") return Qt.rgba(0.0, 0.6, 0.3, 0.25);
        if (tone === "info")    return Qt.rgba(0.0, 0.4, 0.8, 0.25);
        if (tone === "warning") return Qt.rgba(0.8, 0.6, 0.0, 0.25);
        return Qt.rgba(0.5, 0.5, 0.5, 0.15);
    }

    Text {
        id: label
        anchors.centerIn: parent
        text: root.text
        font.pixelSize: 12
        font.weight: Font.DemiBold
        color: {
            if (root.tone === "success") return "#0d6832";
            if (root.tone === "info")    return "#0a5caa";
            if (root.tone === "warning") return "#7a5200";
            return palette.windowText;
        }
    }
}
