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

    signal settingsRequested()

    title: streamData ? streamData.displayName : ""
    subtitle: streamData
        ? (streamData.payloadType + " \u00b7 " + streamData.sampleRateText)
        : ""

    visible: !detached

    Label {
        Layout.fillWidth: true
        text: streamData ? streamData.summaryText : ""
        color: palette.placeholderText
        font.pixelSize: 12
    }

    Label {
        Layout.fillWidth: true
        text: streamData ? streamData.channelSummary : ""
        color: palette.placeholderText
        font.pixelSize: 11
        wrapMode: Text.Wrap
        visible: text.length > 0
    }

    RowLayout {
        Layout.fillWidth: true
        Layout.topMargin: 2
        spacing: 4

        Item { Layout.fillWidth: true }

        Button {
            text: "\u2699"
            flat: true
            implicitWidth: 32
            implicitHeight: 32
            ToolTip.text: "预览设置"
            ToolTip.visible: hovered
            onClicked: root.settingsRequested()
        }

        Button {
            text: root.detached ? "\u2b1c" : "\u2197"
            flat: true
            implicitWidth: 32
            implicitHeight: 32
            ToolTip.text: root.detached ? "收回窗口" : "弹出窗口"
            ToolTip.visible: hovered
            onClicked: root.detached = !root.detached
        }
    }

    // Embedded preview content
    Loader {
        id: embeddedPreview
        Layout.fillWidth: true
        Layout.preferredHeight: {
            if (!streamData) return 200;
            if (streamData.payloadType === "signal") return 260;
            return 220;
        }
        active: !root.detached
        sourceComponent: {
            if (!streamData) return emptyComponent;
            if (streamData.payloadType === "signal") return signalComponent;
            return textureComponent;
        }
    }

    // Detached preview window
    QW.Window {
        id: detachedWindow
        visible: root.detached
        width: 960
        height: 640
        title: streamData ? streamData.displayName : "Preview"

        onClosing: function(close) {
            root.detached = false;
            close.accepted = false;
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 8
            spacing: 8

            RowLayout {
                Layout.fillWidth: true

                Label {
                    text: streamData ? streamData.displayName : ""
                    font.pixelSize: 16
                    font.weight: Font.DemiBold
                }

                Label {
                    text: streamData ? streamData.summaryText : ""
                    color: palette.placeholderText
                    font.pixelSize: 12
                }

                Item { Layout.fillWidth: true }

                Button {
                    text: "\u2b1c 收回"
                    onClicked: root.detached = false
                }
            }

            Loader {
                id: detachedPreview
                Layout.fillWidth: true
                Layout.fillHeight: true
                active: root.detached
                sourceComponent: {
                    if (!streamData) return emptyComponent;
                    if (streamData.payloadType === "signal") return signalComponent;
                    return textureComponent;
                }
            }
        }
    }

    // --- Shared Preview Components ---

    Component {
        id: signalComponent
        WaveformItem {
            id: waveformItem
            anchors.fill: parent

            property var ctrl: root.streamData ? root.streamData.controller : null

            channelData: ctrl ? ctrl.channelData : []
            channelNames: ctrl ? ctrl.channelNames : []
            sampleRateHz: ctrl ? ctrl.sampleRateHz : 250
            layoutMode: ctrl ? ctrl.layoutMode : "expanded"
            yRangeMode: ctrl ? ctrl.yRangeMode : "auto"
            manualYMin: ctrl ? ctrl.manualYMin : -1.0
            manualYMax: ctrl ? ctrl.manualYMax : 1.0
        }
    }

    Component {
        id: textureComponent
        TextureItem {
            id: textureItem
            anchors.fill: parent

            property var ctrl: root.streamData ? root.streamData.controller : null

            fillMode: ctrl ? ctrl.fillMode : "fit"

            Connections {
                target: ctrl
                function onImageChanged(image) {
                    textureItem.setSourceImage(image);
                }
            }
        }
    }

    Component {
        id: emptyComponent
        Rectangle {
            anchors.fill: parent
            color: palette.alternateBase
            radius: 6

            Label {
                anchors.centerIn: parent
                text: "等待数据"
                color: palette.placeholderText
            }
        }
    }
}
