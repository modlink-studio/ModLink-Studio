import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "components"
import "pages"

ApplicationWindow {
    id: root

    width: 1460
    height: 920
    visible: true
    title: appController.applicationTitle
    color: "#edf3f8"

    property int currentPageIndex: 0
    property string flashMessage: ""

    function showFlash(message) {
        if (!message || message.length === 0) {
            return;
        }
        flashMessage = message;
        flashTimer.restart();
    }

    Timer {
        id: flashTimer
        interval: 3600
        repeat: false
        onTriggered: root.flashMessage = ""
    }

    Connections {
        target: appController.mainPage
        function onMessageRaised(message) { root.showFlash(message); }
    }

    Connections {
        target: appController.devicePage
        function onMessageRaised(message) { root.showFlash(message); }
    }

    Connections {
        target: appController.settingsPage
        function onMessageRaised(message) { root.showFlash(message); }
    }

    header: Rectangle {
        height: 72
        color: "#f9fbfd"
        border.width: 1
        border.color: "#d8e4f0"

        RowLayout {
            anchors.fill: parent
            anchors.margins: 18
            spacing: 12

            ColumnLayout {
                spacing: 2

                Label {
                    text: "ModLink Studio"
                    font.pixelSize: 24
                    font.weight: Font.Bold
                    color: "#102235"
                }

                Label {
                    text: "QML 迁移线"
                    color: "#5f7288"
                }
            }

            Item { Layout.fillWidth: true }

            Rectangle {
                Layout.preferredWidth: 380
                Layout.preferredHeight: 42
                radius: 16
                color: root.flashMessage.length > 0 ? "#d7ebff" : "#eef3f7"
                border.width: 1
                border.color: root.flashMessage.length > 0 ? "#9fc5ef" : "#d8e4f0"

                Label {
                    anchors.centerIn: parent
                    width: parent.width - 24
                    text: root.flashMessage.length > 0
                        ? root.flashMessage
                        : "共享 core/sdk/settings，逐步替换旧 UI。"
                    horizontalAlignment: Text.AlignHCenter
                    color: root.flashMessage.length > 0 ? "#0f5cab" : "#5f7288"
                    elide: Text.ElideRight
                }
            }
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 18

        Rectangle {
            Layout.preferredWidth: 220
            Layout.fillHeight: true
            radius: 26
            color: "#f9fbfd"
            border.width: 1
            border.color: "#d8e4f0"

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 18
                spacing: 12

                Label {
                    text: "导航"
                    font.pixelSize: 18
                    font.weight: Font.DemiBold
                    color: "#102235"
                }

                NavButton {
                    text: "实时展示"
                    active: root.currentPageIndex === 0
                    onClicked: root.currentPageIndex = 0
                }

                NavButton {
                    text: "设备"
                    active: root.currentPageIndex === 1
                    onClicked: root.currentPageIndex = 1
                }

                NavButton {
                    text: "设置"
                    active: root.currentPageIndex === 2
                    onClicked: root.currentPageIndex = 2
                }

                Item { Layout.fillHeight: true }

                Rectangle {
                    Layout.fillWidth: true
                    radius: 18
                    color: "#eef5fb"
                    border.width: 1
                    border.color: "#d7e3ef"
                    implicitHeight: 120

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 6

                        Label {
                            text: "迁移状态"
                            font.pixelSize: 16
                            font.weight: Font.DemiBold
                            color: "#102235"
                        }

                        Label {
                            text: "旧 UI 继续交付，新 UI 用 QML 重建三页骨架。"
                            wrapMode: Text.Wrap
                            color: "#5f7288"
                        }
                    }
                }
            }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: root.currentPageIndex

            MainPage { controller: appController.mainPage }
            DevicePage { controller: appController.devicePage }
            SettingsPage { controller: appController.settingsPage }
        }
    }
}
