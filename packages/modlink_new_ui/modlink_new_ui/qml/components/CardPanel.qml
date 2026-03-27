import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root

    property string title: ""
    property string subtitle: ""
    default property alias contentData: contentColumn.data

    radius: 22
    color: "#fbfdff"
    border.width: 1
    border.color: "#d8e4f0"

    implicitWidth: 360
    implicitHeight: contentColumn.implicitHeight + 36

    ColumnLayout {
        id: contentColumn
        anchors.fill: parent
        anchors.margins: 18
        spacing: 12

        Item {
            Layout.fillWidth: true
            visible: root.title.length > 0 || root.subtitle.length > 0
            implicitHeight: headerColumn.implicitHeight

            ColumnLayout {
                id: headerColumn
                anchors.fill: parent
                spacing: 4

                Label {
                    text: root.title
                    font.pixelSize: 18
                    font.weight: Font.DemiBold
                    color: "#102235"
                    visible: text.length > 0
                }

                Label {
                    text: root.subtitle
                    color: "#5f7288"
                    font.pixelSize: 13
                    wrapMode: Text.Wrap
                    visible: text.length > 0
                }
            }
        }
    }
}
