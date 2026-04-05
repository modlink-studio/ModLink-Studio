import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window as QW
import ModLink.GPU 1.0
import "../components"

CardPanel {
    id: root

    property var streamData: null
    property bool detached: false
    readonly property var ctrl: streamData ? streamData.controller : null
    objectName: streamData ? streamData.objectName : "streamPreviewCard"

    UiTokens { id: ui }

    title: ""
    subtitle: ""
    visible: !detached

    function openSettingsDialog() {
        if (!ctrl) return;
        settingsDialog.open();
    }

    ColumnLayout {
        Layout.fillWidth: true
        spacing: 14

        RowLayout {
            Layout.fillWidth: true
            spacing: 10

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 5

                Label {
                    text: streamData ? streamData.displayName : ""
                    font.pixelSize: 16
                    font.weight: Font.DemiBold
                    color: ui.textPrimary
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 6

                    StatusPill {
                        text: streamData ? streamData.payloadType : ""
                        tone: "info"
                    }

                    Label {
                        text: streamData ? streamData.sampleRateText : ""
                        font.pixelSize: 12
                        color: ui.textSecondary
                    }
                }
            }

            RowLayout {
                spacing: 4

                ToolButton {
                    text: "\u2699"
                    focusPolicy: Qt.NoFocus
                    implicitWidth: 34
                    implicitHeight: 34
                    onClicked: root.openSettingsDialog()
                }

                ToolButton {
                    text: root.detached ? "\u2b1c" : "\u2197"
                    focusPolicy: Qt.NoFocus
                    implicitWidth: 34
                    implicitHeight: 34
                    onClicked: root.detached = !root.detached
                }
            }
        }

        Label {
            Layout.fillWidth: true
            text: streamData ? streamData.summaryText : ""
            font.pixelSize: 12
            wrapMode: Text.Wrap
            color: ui.textSecondary
        }

        Label {
            Layout.fillWidth: true
            text: streamData ? streamData.channelSummary : ""
            visible: text.length > 0
            font.pixelSize: 11
            wrapMode: Text.Wrap
            color: ui.textMuted
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: {
                if (!streamData) return 220;
                if (streamData.payloadType === "signal") return 286;
                return 256;
            }
            radius: ui.radiusLg
            color: ui.previewStage
            border.width: 1
            border.color: "#223645"

            Loader {
                id: embeddedPreview
                anchors.fill: parent
                anchors.margins: 12
                active: !root.detached
                sourceComponent: {
                    if (!streamData) return emptyComponent;
                    if (streamData.payloadType === "signal") return signalComponent;
                    return textureComponent;
                }
            }
        }
    }

    Dialog {
        id: settingsDialog
        objectName: root.objectName + "_settingsDialog"
        title: (streamData ? streamData.displayName : "") + " · 预览设置"
        modal: true
        width: 456
        standardButtons: Dialog.Close

        contentItem: Pane {
            implicitWidth: 420
            implicitHeight: 460
            padding: 16
            ColumnLayout {
                anchors.fill: parent
                spacing: 14

                Label {
                    text: "检查器"
                    font.pixelSize: 12
                    font.weight: Font.DemiBold
                    color: ui.textMuted
                }

                Loader {
                    Layout.fillWidth: true
                    active: !!root.ctrl
                    sourceComponent: {
                        if (!root.streamData) return null;
                        if (root.streamData.payloadType === "signal") return signalSettingsComponent;
                        if (root.streamData.payloadType === "raster") return rasterSettingsComponent;
                        if (root.streamData.payloadType === "field") return fieldSettingsComponent;
                        if (root.streamData.payloadType === "video") return videoSettingsComponent;
                        return null;
                    }
                }
            }
        }
    }

    QW.Window {
        id: detachedWindow
        visible: root.detached
        width: 960
        height: 640
        color: ui.contentBg
        title: streamData ? streamData.displayName : "Preview"

        onClosing: function(close) {
            root.detached = false;
            close.accepted = false;
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: ui.pageGutter
            spacing: 12

            RowLayout {
                Layout.fillWidth: true
                spacing: 10

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4

                    Label {
                        text: streamData ? streamData.displayName : ""
                        font.pixelSize: 22
                        font.weight: Font.DemiBold
                        color: ui.textPrimary
                    }

                    Label {
                        text: streamData ? streamData.summaryText : ""
                        font.pixelSize: 13
                        color: ui.textSecondary
                    }
                }

                Button {
                    text: "\u2b1c 收回"
                    highlighted: true
                    onClicked: root.detached = false
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: ui.radiusLg
                color: ui.previewStage
                border.width: 1
                border.color: "#223645"

                Loader {
                    id: detachedPreview
                    anchors.fill: parent
                    anchors.margins: 14
                    active: root.detached
                    sourceComponent: {
                        if (!streamData) return emptyComponent;
                        if (streamData.payloadType === "signal") return signalComponent;
                        return textureComponent;
                    }
                }
            }
        }
    }

    Component {
        id: signalComponent
        WaveformItem {
            anchors.fill: parent
            channelData: root.ctrl ? root.ctrl.channelData : []
            channelNames: root.ctrl ? root.ctrl.channelNames : []
            sampleRateHz: root.ctrl ? root.ctrl.sampleRateHz : 250
            layoutMode: root.ctrl ? root.ctrl.layoutMode : "expanded"
            yRangeMode: root.ctrl ? root.ctrl.yRangeMode : "auto"
            manualYMin: root.ctrl ? root.ctrl.manualYMin : -1.0
            manualYMax: root.ctrl ? root.ctrl.manualYMax : 1.0
        }
    }

    Component {
        id: textureComponent
        TextureItem {
            id: textureItem
            anchors.fill: parent
            fillMode: root.ctrl ? root.ctrl.fillMode : "fit"
            sourceImage: root.ctrl ? root.ctrl.currentImage : null
        }
    }

    Component {
        id: emptyComponent
        Rectangle {
            anchors.fill: parent
            color: "transparent"

            ColumnLayout {
                anchors.centerIn: parent
                spacing: 6

                Label {
                    text: "No preview yet"
                    font.pixelSize: 16
                    font.weight: Font.DemiBold
                    color: "#e8eef3"
                    horizontalAlignment: Text.AlignHCenter
                }

                Label {
                    text: "连接并启动数据流后，画面会自动出现在这里。"
                    font.pixelSize: 12
                    color: "#9eb0bf"
                    horizontalAlignment: Text.AlignHCenter
                }
            }
        }
    }

    Component {
        id: signalSettingsComponent
        SignalPreviewSettingsForm { controller: root.ctrl }
    }

    Component {
        id: rasterSettingsComponent
        RasterPreviewSettingsForm { controller: root.ctrl }
    }

    Component {
        id: fieldSettingsComponent
        FieldPreviewSettingsForm { controller: root.ctrl }
    }

    Component {
        id: videoSettingsComponent
        VideoPreviewSettingsForm { controller: root.ctrl }
    }
}
