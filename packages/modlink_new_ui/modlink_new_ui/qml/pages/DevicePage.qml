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
        spacing: 16

        Label {
            text: controller.portals.length > 0 ? "设备管理" : "当前没有可用 driver"
            font.pixelSize: 22
            font.weight: Font.DemiBold
            color: "#102235"
        }

        Repeater {
            model: controller.portals

            delegate: CardPanel {
                id: portalCard
                Layout.fillWidth: true
                width: root.availableWidth
                property string driverId: modelData.driverId
                property bool portalBusy: modelData.busy
                title: modelData.title
                subtitle: modelData.description

                RowLayout {
                    Layout.fillWidth: true

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

                Label {
                    Layout.fillWidth: true
                    text: modelData.connectedSubtitle
                    color: "#5f7288"
                    wrapMode: Text.Wrap
                    visible: text.length > 0
                }

                RowLayout {
                    Layout.fillWidth: true
                    visible: modelData.isConnected

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

                ColumnLayout {
                    Layout.fillWidth: true
                    visible: !modelData.isConnected && modelData.searchResults.length > 0
                    spacing: 8

                    Repeater {
                        model: modelData.searchResults

                        delegate: Rectangle {
                            Layout.fillWidth: true
                            radius: 16
                            color: "#f4f8fc"
                            border.width: 1
                            border.color: "#d8e4f0"
                            implicitHeight: 74

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 14
                                spacing: 12

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 2

                                    Label {
                                        text: modelData.title
                                        font.pixelSize: 15
                                        font.weight: Font.DemiBold
                                        color: "#102235"
                                    }

                                    Label {
                                        text: modelData.subtitle
                                        color: "#5f7288"
                                        wrapMode: Text.Wrap
                                    }
                                }

                                Button {
                                    text: "连接"
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
                    color: "#b42318"
                    wrapMode: Text.Wrap
                    visible: text.length > 0
                }
            }
        }
    }
}
