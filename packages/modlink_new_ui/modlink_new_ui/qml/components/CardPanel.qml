import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Effects

Rectangle {
    id: root

    property string title: ""
    property string subtitle: ""
    default property alias contentData: contentColumn.data

    radius: 8
    color: palette.base
    border.width: 1
    border.color: palette.mid

    implicitWidth: 360
    implicitHeight: contentColumn.implicitHeight + 32

    layer.enabled: true
    layer.effect: MultiEffect {
        shadowEnabled: true
        shadowColor: Qt.rgba(0, 0, 0, 0.06)
        shadowBlur: 0.3
        shadowVerticalOffset: 2
        shadowHorizontalOffset: 0
    }

    ColumnLayout {
        id: contentColumn
        anchors.fill: parent
        anchors.margins: 16
        spacing: 10

        Item {
            Layout.fillWidth: true
            visible: root.title.length > 0 || root.subtitle.length > 0
            implicitHeight: headerCol.implicitHeight

            ColumnLayout {
                id: headerCol
                anchors.fill: parent
                spacing: 2

                Label {
                    text: root.title
                    font.pixelSize: 16
                    font.weight: Font.DemiBold
                    color: palette.windowText
                    visible: text.length > 0
                }

                Label {
                    text: root.subtitle
                    color: palette.placeholderText
                    font.pixelSize: 12
                    wrapMode: Text.Wrap
                    visible: text.length > 0
                }
            }
        }
    }
}
