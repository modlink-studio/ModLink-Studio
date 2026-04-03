import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "components"
import "pages"

ApplicationWindow {
    id: root

    width: 1480
    height: 960
    visible: true
    title: "ModLink Studio"
    color: palette.window

    property int currentPageIndex: 0
    property string flashMessage: ""

    function showFlash(message) {
        if (!message || message.length === 0) return;
        flashMessage = message;
        flashTimer.restart();
    }

    Timer {
        id: flashTimer
        interval: 4000
        repeat: false
        onTriggered: root.flashMessage = ""
    }

    Connections {
        target: appController ? appController.mainPage : null
        function onMessageRaised(message) { root.showFlash(message); }
    }
    Connections {
        target: appController ? appController.devicePage : null
        function onMessageRaised(message) { root.showFlash(message); }
    }
    Connections {
        target: appController ? appController.settingsPage : null
        function onMessageRaised(message) { root.showFlash(message); }
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        // --- Sidebar Navigation ---
        Rectangle {
            Layout.preferredWidth: 220
            Layout.fillHeight: true
            color: Qt.darker(palette.window, 1.03)

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 4

                // App title
                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.bottomMargin: 16
                    spacing: 2

                    Label {
                        text: "ModLink Studio"
                        font.pixelSize: 20
                        font.weight: Font.Bold
                        color: palette.windowText
                    }

                    Label {
                        text: "v0.2.0"
                        font.pixelSize: 12
                        color: palette.placeholderText
                    }
                }

                // Nav items
                Repeater {
                    model: [
                        { label: "实时展示", idx: 0 },
                        { label: "设备",     idx: 1 },
                        { label: "设置",     idx: 2 }
                    ]

                    delegate: Button {
                        Layout.fillWidth: true
                        text: modelData.label
                        flat: true
                        highlighted: root.currentPageIndex === modelData.idx
                        onClicked: root.currentPageIndex = modelData.idx
                        leftPadding: 16
                        rightPadding: 16
                        topPadding: 10
                        bottomPadding: 10
                        font.weight: root.currentPageIndex === modelData.idx ? Font.DemiBold : Font.Normal
                    }
                }

                Item { Layout.fillHeight: true }

                // Flash message area
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: flashLabel.implicitHeight + 20
                    radius: 8
                    color: root.flashMessage.length > 0
                        ? Qt.rgba(palette.highlight.r, palette.highlight.g, palette.highlight.b, 0.12)
                        : "transparent"
                    border.width: root.flashMessage.length > 0 ? 1 : 0
                    border.color: Qt.rgba(palette.highlight.r, palette.highlight.g, palette.highlight.b, 0.3)
                    visible: root.flashMessage.length > 0

                    Label {
                        id: flashLabel
                        anchors.centerIn: parent
                        width: parent.width - 16
                        text: root.flashMessage
                        wrapMode: Text.Wrap
                        color: palette.highlight
                        font.pixelSize: 12
                        horizontalAlignment: Text.AlignHCenter
                    }

                    Behavior on opacity { NumberAnimation { duration: 200 } }
                }
            }
        }

        // --- Separator ---
        Rectangle {
            Layout.preferredWidth: 1
            Layout.fillHeight: true
            color: palette.mid
        }

        // --- Content Area ---
        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: root.currentPageIndex

            MainPage { controller: appController ? appController.mainPage : null }
            DevicePage { controller: appController ? appController.devicePage : null }
            SettingsPage { controller: appController ? appController.settingsPage : null }
        }
    }
}
