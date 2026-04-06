import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal
import QtQuick.Layouts
import "components"
import "pages"

ApplicationWindow {
    id: root

    UiTokens { id: ui }

    width: 1480
    height: 960
    visible: true
    title: "ModLink Studio"
    color: ui.windowBg

    Universal.theme: Universal.Light
    Universal.accent: Universal.Teal

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

        Rectangle {
            Layout.preferredWidth: 252
            Layout.fillHeight: true
            color: ui.sidebarBg

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 20
                spacing: 12

                Rectangle {
                    Layout.fillWidth: true
                    radius: ui.radiusLg
                    color: ui.sidebarSurface
                    border.width: 1
                    border.color: ui.sidebarBorder
                    implicitHeight: 110

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 18
                        spacing: 5

                        Label {
                            text: "ModLink Studio"
                            font.pixelSize: 22
                            font.weight: Font.DemiBold
                            color: ui.textOnDark
                        }

                        Label {
                            text: "实时采集 · 设备联动 · 可视化工作台"
                            wrapMode: Text.Wrap
                            font.pixelSize: 12
                            color: ui.textOnDarkMuted
                        }
                    }
                }

                Label {
                    text: "Workspace"
                    font.pixelSize: 11
                    font.weight: Font.DemiBold
                    color: ui.textOnDarkMuted
                    Layout.topMargin: 8
                    Layout.leftMargin: 8
                }

                Repeater {
                    model: [
                        { label: "实时展示", caption: "预览流与录制控制", idx: 0 },
                        { label: "设备", caption: "连接、搜索与运行状态", idx: 1 },
                        { label: "设置", caption: "路径、刷新率与标签", idx: 2 }
                    ]

                    delegate: ItemDelegate {
                        Layout.fillWidth: true
                        implicitHeight: 70
                        hoverEnabled: true
                        highlighted: root.currentPageIndex === modelData.idx
                        padding: 0

                        background: Rectangle {
                            radius: ui.radiusMd
                            color: root.currentPageIndex === modelData.idx
                                ? ui.sidebarSurface
                                : (parent.hovered ? Qt.rgba(1, 1, 1, 0.04) : "transparent")
                            border.width: root.currentPageIndex === modelData.idx ? 1 : 0
                            border.color: ui.sidebarBorder
                        }

                        contentItem: RowLayout {
                            spacing: 14

                            Rectangle {
                                width: 4
                                height: 34
                                radius: 2
                                color: root.currentPageIndex === modelData.idx ? ui.accent : "transparent"
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2

                                Label {
                                    text: modelData.label
                                    font.pixelSize: 14
                                    font.weight: root.currentPageIndex === modelData.idx ? Font.DemiBold : Font.Medium
                                    color: ui.textOnDark
                                }

                                Label {
                                    text: modelData.caption
                                    wrapMode: Text.Wrap
                                    font.pixelSize: 11
                                    color: ui.textOnDarkMuted
                                }
                            }
                        }

                        onClicked: root.currentPageIndex = modelData.idx
                    }
                }

                Item { Layout.fillHeight: true }

                Rectangle {
                    Layout.fillWidth: true
                    radius: ui.radiusLg
                    color: ui.sidebarSurface
                    border.width: 1
                    border.color: ui.sidebarBorder
                    implicitHeight: 84

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 4

                        Label {
                            text: "v0.2.0"
                            font.pixelSize: 12
                            font.weight: Font.DemiBold
                            color: ui.textOnDark
                        }

                        Label {
                            text: "QML 工作台入口仍是实验态，但预览、设备与设置已经收进同一套桌面壳层。"
                            wrapMode: Text.Wrap
                            font.pixelSize: 11
                            color: ui.textOnDarkMuted
                        }
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: ui.contentBg

            Item {
                anchors.fill: parent

                Item {
                    id: contentFrame
                    width: Math.max(0, Math.min(parent.width - 40, 1280))
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    anchors.horizontalCenter: parent.horizontalCenter

                    StackLayout {
                        anchors.fill: parent
                        currentIndex: root.currentPageIndex

                        MainPage { controller: appController ? appController.mainPage : null }
                        DevicePage { controller: appController ? appController.devicePage : null }
                        SettingsPage { controller: appController ? appController.settingsPage : null }
                    }
                }
            }
        }
    }

    Frame {
        anchors.top: parent.top
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.topMargin: 20
        width: Math.min(540, parent.width - 48)
        visible: root.flashMessage.length > 0
        z: 10

        background: Rectangle {
            radius: ui.radiusLg
            color: ui.surface
            border.width: 1
            border.color: ui.borderSoft
        }

        Label {
            width: parent.width - 28
            wrapMode: Text.Wrap
            horizontalAlignment: Text.AlignHCenter
            text: root.flashMessage
            font.pixelSize: 13
            font.weight: Font.Medium
            color: ui.textPrimary
        }
    }
}
