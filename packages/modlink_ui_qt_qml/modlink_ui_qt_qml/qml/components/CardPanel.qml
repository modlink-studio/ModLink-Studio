import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root

    property string title: ""
    property string subtitle: ""
    default property alias contentData: contentColumn.data

    UiTokens { id: ui }

    implicitWidth: 360
    implicitHeight: contentColumn.implicitHeight + ui.cardPadding * 2
    radius: ui.radiusLg
    color: ui.surface
    border.width: 1
    border.color: ui.borderSoft

    ColumnLayout {
        id: contentColumn
        anchors.fill: parent
        anchors.margins: ui.cardPadding
        spacing: 14

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
                    visible: text.length > 0
                    font.pixelSize: 17
                    font.weight: Font.DemiBold
                    color: ui.textPrimary
                }

                Label {
                    text: root.subtitle
                    visible: text.length > 0
                    font.pixelSize: 12
                    wrapMode: Text.Wrap
                    color: ui.textSecondary
                }
            }
        }
    }
}
