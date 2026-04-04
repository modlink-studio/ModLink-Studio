import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root

    property string title: ""
    property string subtitle: ""
    default property alias trailingContent: trailingRow.data

    UiTokens { id: ui }

    implicitHeight: headerRow.implicitHeight

    RowLayout {
        id: headerRow
        anchors.fill: parent
        spacing: 18

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 4

            Label {
                text: root.title
                font.pixelSize: 30
                font.weight: Font.DemiBold
                color: ui.textPrimary
            }

            Label {
                visible: text.length > 0
                text: root.subtitle
                font.pixelSize: 13
                wrapMode: Text.Wrap
                color: ui.textSecondary
            }
        }

        RowLayout {
            id: trailingRow
            spacing: 10
        }
    }
}
