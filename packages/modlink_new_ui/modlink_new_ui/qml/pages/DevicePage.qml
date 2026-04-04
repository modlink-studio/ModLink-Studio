import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

ScrollView {
    id: root

    property var controller

    UiTokens { id: ui }

    clip: true
    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

    ColumnLayout {
        x: ui.pageGutter
        y: ui.pageGutter
        width: Math.max(root.availableWidth - ui.pageGutter * 2, 0)
        spacing: ui.sectionGap

        PageHeader {
            Layout.fillWidth: true
            title: "设备"
            subtitle: (controller && controller.portals && controller.portals.length > 0)
                ? "搜索、连接、断开和启停流都集中在这里完成。"
                : "当前没有可用 driver。"
        }

        Repeater {
            model: controller ? controller.portals : []

            delegate: CardPanel {
                id: portalCard
                Layout.fillWidth: true

                property string driverId: modelData.driverId
                property bool portalBusy: modelData.busy

                title: modelData.title
                subtitle: modelData.description

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    StatusPill {
                        text: modelData.statusText
                        tone: modelData.statusTone
                    }

                    Label {
                        Layout.fillWidth: true
                        text: modelData.connectedSubtitle
                        visible: text.length > 0
                        font.pixelSize: 12
                        wrapMode: Text.Wrap
                        color: ui.textSecondary
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    visible: modelData.hasProviders && !modelData.isConnected
                    spacing: 10

                    ComboBox {
                        Layout.preferredWidth: 220
                        enabled: !modelData.busy
                        model: modelData.providers
                        currentIndex: Math.max(0, modelData.providers.indexOf(modelData.selectedProvider))
                        onActivated: controller.setSelectedProvider(portalCard.driverId, currentText)
                    }

                    Button {
                        text: modelData.searchButtonText
                        highlighted: true
                        enabled: modelData.hasProviders && !modelData.busy
                        onClicked: controller.search(portalCard.driverId)
                    }

                    Item { Layout.fillWidth: true }
                }

                RowLayout {
                    Layout.fillWidth: true
                    visible: modelData.isConnected
                    spacing: 10

                    Button {
                        text: modelData.streamButtonText
                        highlighted: !modelData.isStreaming
                        enabled: !modelData.busy
                        onClicked: controller.toggleStreaming(portalCard.driverId)
                    }

                    Button {
                        text: "断开连接"
                        enabled: !modelData.busy
                        onClicked: controller.disconnectDevice(portalCard.driverId)
                    }

                    Item { Layout.fillWidth: true }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    visible: !modelData.isConnected && modelData.searchResults.length > 0
                    spacing: 8

                    Repeater {
                        model: modelData.searchResults

                        delegate: Frame {
                            Layout.fillWidth: true
                            padding: 16

                            background: Rectangle {
                                radius: ui.radiusMd
                                color: ui.surfaceAlt
                                border.width: 1
                                border.color: ui.borderSoft
                            }

                            RowLayout {
                                anchors.fill: parent
                                spacing: 12

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 3

                                    Label {
                                        text: modelData.title
                                        font.pixelSize: 14
                                        font.weight: Font.DemiBold
                                        color: ui.textPrimary
                                    }

                                    Label {
                                        text: modelData.subtitle
                                        font.pixelSize: 12
                                        wrapMode: Text.Wrap
                                        color: ui.textSecondary
                                    }
                                }

                                Button {
                                    text: "连接"
                                    highlighted: true
                                    enabled: !portalCard.portalBusy
                                    onClicked: controller.connectDevice(portalCard.driverId, index)
                                }
                            }
                        }
                    }
                }

                Label {
                    Layout.fillWidth: true
                    text: modelData.errorText
                    visible: text.length > 0
                    font.pixelSize: 12
                    wrapMode: Text.Wrap
                    color: ui.dangerFg
                }
            }
        }

        Item { Layout.fillHeight: true }
    }
}
