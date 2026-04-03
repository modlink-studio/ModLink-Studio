import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import "../preview"

Item {
    id: root

    property var controller
    readonly property var _acq: controller ? controller.acquisition : null

    ScrollView {
        id: scrollView
        anchors.fill: parent
        anchors.margins: 16
        clip: true
        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

        ColumnLayout {
            width: scrollView.availableWidth
            spacing: 14

            Label {
                text: (controller && controller.previews && controller.previews.length > 0)
                    ? "实时预览"
                    : "当前没有可预览的流"
                font.pixelSize: 20
                font.weight: Font.DemiBold
                color: palette.windowText
            }

            GridLayout {
                Layout.fillWidth: true
                columns: scrollView.availableWidth >= 1100 ? 2 : 1
                rowSpacing: 14
                columnSpacing: 14

                Repeater {
                    model: controller ? controller.previews : []

                    delegate: StreamPreviewCard {
                        Layout.fillWidth: true
                        streamData: modelData
                    }
                }
            }

            Item {
                Layout.fillWidth: true
                Layout.preferredHeight: acquisitionPanel.visible ? acquisitionPanel.height + 24 : 0
            }
        }
    }

    CardPanel {
        id: acquisitionPanel
        title: (_acq && _acq.isRecording) ? "录制进行中" : "采集控制"
        subtitle: _acq ? ("输出目录：" + _acq.outputDirectory) : ""

        anchors.bottom: parent.bottom
        anchors.bottomMargin: 12
        anchors.horizontalCenter: parent.horizontalCenter
        width: Math.min(1100, parent.width - 32)
        visible: !!controller

        GridLayout {
            Layout.fillWidth: true
            columns: acquisitionPanel.width >= 800 ? 4 : 2
            rowSpacing: 8
            columnSpacing: 8

            TextField {
                Layout.fillWidth: true
                placeholderText: "Session 名称"
                text: _acq ? _acq.sessionName : ""
                onTextEdited: { if (_acq) _acq.setSessionName(text); }
            }

            ComboBox {
                Layout.fillWidth: true
                model: _acq ? _acq.recordingLabels : []
                editable: true
                editText: _acq ? _acq.recordingLabel : ""
                onEditTextChanged: { if (_acq) _acq.setRecordingLabel(editText); }
            }

            TextField {
                Layout.fillWidth: true
                placeholderText: "Marker 标签"
                text: _acq ? _acq.markerLabel : ""
                onTextEdited: { if (_acq) _acq.setMarkerLabel(text); }
            }

            TextField {
                Layout.fillWidth: true
                placeholderText: "区间标签"
                text: _acq ? _acq.segmentLabel : ""
                onTextEdited: { if (_acq) _acq.setSegmentLabel(text); }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            Button {
                text: _acq ? _acq.primaryActionText : "开始采集"
                highlighted: true
                onClicked: { if (_acq) _acq.toggleRecording(); }
            }

            Button {
                text: "插入 Marker"
                enabled: _acq ? _acq.isRecording : false
                onClicked: { if (_acq) _acq.insertMarker(); }
            }

            Button {
                text: _acq ? _acq.toggleSegmentText : "开始区间"
                enabled: _acq ? _acq.isRecording : false
                onClicked: { if (_acq) _acq.toggleSegment(); }
            }

            Button {
                text: "清空区间"
                enabled: _acq ? (_acq.isRecording && _acq.isSegmentActive) : false
                onClicked: { if (_acq) _acq.resetSegment(); }
            }

            Item { Layout.fillWidth: true }
        }
    }
}
