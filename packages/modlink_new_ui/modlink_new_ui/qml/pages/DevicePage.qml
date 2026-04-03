import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

ScrollView {
    id: root

    property var controller

    clip: true
    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

    ColumnLayout {
        width: root.availableWidth
        spacing: 14

        Label {
            text: (controller && controller.portals && controller.portals.length > 0) ? "设备管理" : "当前没有可用 driver"
            font.pixelSize: 20
            font.weight: Font.DemiBold
            color: palette.windowText
            Layout.leftMargin: 16
            Layout.topMargin: 16
        }

        Repeater {
            model: controller ? controller.portals : []

            delegate: CardPanel {
                id: portalCard
                Layout.fillWidth: true
                Layout.leftMargin: 16
                Layout.rightMargin: 16

                property string driverId: modelData.driverId
                property bool portalBusy: modelData.busy

                title: modelData.title
                subtitle: modelData.description

                // Status + provider row
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    StatusPill {
                        text: modelData.statusText
                        tone: modelData.statusTone
                    }

                    Item { Layout.fillWidth: true }

                    ComboBox {
                        Layout.preferredWidth: 180
                        enabled: modelData.hasProviders && !modelData.busy && !modelData.isConnected
                        model: modelData.providers
                        currentIndex: Math.max(0, modelData.providers.indexOf(modelData.selectedProvider))
                        onActivated: controller.setSelectedProvider(portalCard.driverId, currentText)
                    }

                    Button {
                        text: modelData.searchButtonText
                        enabled: modelData.hasProviders && !modelData.busy && !modelData.isConnected
                        onClicked: controller.search(portalCard.driverId)
                    }
                }

                // Connected subtitle
                Label {
                    Layout.fillWidth: true
                    text: modelData.connectedSubtitle
                    color: palette.placeholderText
                    font.pixelSize: 12
                    wrapMode: Text.Wrap
                    visible: text.length > 0
                }

                // Connected device controls
                RowLayout {
                    Layout.fillWidth: true
                    visible: modelData.isConnected
                    spacing: 8

                    Button {
                        text: modelData.streamButtonText
                        enabled: !modelData.busy
                        highlighted: modelData.isStreaming
                        onClicked: controller.toggleStreaming(portalCard.driverId)
                    }

                    Button {
                        text: "断开连接"
                        enabled: !modelData.busy
                        onClicked: controller.disconnectDevice(portalCard.driverId)
                    }
                }

                // Search results
                ColumnLayout {
                    Layout.fillWidth: true
                    visible: !modelData.isConnected && modelData.searchResults.length > 0
                    spacing: 6

                    Repeater {
                        model: modelData.searchResults

                        delegate: Rectangle {
                            Layout.fillWidth: true
                            radius: 6
                            color: palette.alternateBase
                            border.width: 1
                            border.color: palette.mid
                            implicitHeight: 64

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 12
                                spacing: 10

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 2

                                    Label {
                                        text: modelData.title
                                        font.pixelSize: 14
                                        font.weight: Font.DemiBold
                                        color: palette.windowText
                                    }

                                    Label {
                                        text: modelData.subtitle
                                        color: palette.placeholderText
                                        font.pixelSize: 12
                                        wrapMode: Text.Wrap
                                    }
                                }

                                Button {
                                    text: "连接"
                                    enabled: !portalCard.portalBusy
                                    highlighted: true
                                    onClicked: controller.connectDevice(portalCard.driverId, index)
                                }
                            }
                        }
                    }
                }

                // Error text
                Label {
                    Layout.fillWidth: true
                    text: modelData.errorText
                    color: "#d13438"
                    font.pixelSize: 12
                    wrapMode: Text.Wrap
                    visible: text.length > 0
                }
            }
        }

        Item { Layout.fillHeight: true }
    }
}
