import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import "../preview"

Item {
    id: root

    property var controller
    readonly property var _acq: controller ? controller.acquisition : null

    UiTokens { id: ui }

    ScrollView {
        id: scrollView
        anchors.fill: parent
        clip: true
        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

        ColumnLayout {
            x: ui.pageGutter
            y: ui.pageGutter
            width: Math.max(scrollView.availableWidth - ui.pageGutter * 2, 0)
            spacing: ui.sectionGap

            PageHeader {
                Layout.fillWidth: true
                title: "实时展示"
                subtitle: (controller && controller.previews && controller.previews.length > 0)
                    ? "统一查看当前所有可预览流，并在同一工作台里完成录制与标注。"
                    : "当前没有可预览的流，连接并启动设备后会自动出现在这里。"
            }

            CardPanel {
                Layout.fillWidth: true
                title: (_acq && _acq.isRecording) ? "录制进行中" : "采集控制"
                subtitle: _acq ? ("输出目录：" + _acq.outputDirectory) : "用于录制、标注和区间控制。"

                GridLayout {
                    Layout.fillWidth: true
                    columns: width >= 1120 ? 3 : 2
                    rowSpacing: 10
                    columnSpacing: 10

                    ComboBox {
                        Layout.fillWidth: true
                        Layout.minimumWidth: 180
                        model: _acq ? _acq.recordingLabels : []
                        editable: true
                        editText: _acq ? _acq.recordingLabel : ""
                        onEditTextChanged: {
                            if (_acq) _acq.setRecordingLabel(editText);
                        }
                    }

                    TextField {
                        Layout.fillWidth: true
                        Layout.minimumWidth: 220
                        placeholderText: "Marker 标签"
                        text: _acq ? _acq.markerLabel : ""
                        onTextEdited: {
                            if (_acq) _acq.setMarkerLabel(text);
                        }
                    }

                    TextField {
                        Layout.fillWidth: true
                        Layout.minimumWidth: 220
                        placeholderText: "区间标签"
                        text: _acq ? _acq.segmentLabel : ""
                        onTextEdited: {
                            if (_acq) _acq.setSegmentLabel(text);
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    Button {
                        text: _acq ? _acq.primaryActionText : "开始采集"
                        highlighted: true
                        onClicked: {
                            if (_acq) _acq.toggleRecording();
                        }
                    }

                    Button {
                        text: "插入 Marker"
                        enabled: _acq ? _acq.isRecording : false
                        onClicked: {
                            if (_acq) _acq.insertMarker();
                        }
                    }

                    Button {
                        text: _acq ? _acq.toggleSegmentText : "开始区间"
                        enabled: _acq ? _acq.isRecording : false
                        onClicked: {
                            if (_acq) _acq.toggleSegment();
                        }
                    }

                    Button {
                        text: "清空区间"
                        enabled: _acq ? (_acq.isRecording && _acq.isSegmentActive) : false
                        onClicked: {
                            if (_acq) _acq.resetSegment();
                        }
                    }

                    Item { Layout.fillWidth: true }

                    StatusPill {
                        visible: !!_acq
                        text: _acq && _acq.isRecording ? "Recording" : "Idle"
                        tone: _acq && _acq.isRecording ? "danger" : "info"
                    }
                }
            }

            GridLayout {
                Layout.fillWidth: true
                columns: width >= 1040 ? 2 : 1
                rowSpacing: 18
                columnSpacing: 18

                Repeater {
                    model: controller ? controller.previews : []

                    delegate: StreamPreviewCard {
                        Layout.fillWidth: true
                        Layout.minimumHeight: modelData.payloadType === "signal" ? 392 : 356
                        streamData: modelData
                    }
                }
            }
        }
    }
}
