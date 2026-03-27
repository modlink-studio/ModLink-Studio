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

        CardPanel {
            Layout.fillWidth: true
            title: controller.acquisition.isRecording ? "录制进行中" : "采集控制"
            subtitle: "新 QML UI 直接复用现有采集后端和 settings。"

            GridLayout {
                Layout.fillWidth: true
                columns: width >= 920 ? 4 : 2
                rowSpacing: 10
                columnSpacing: 10

                TextField {
                    Layout.fillWidth: true
                    placeholderText: "Session 名称"
                    text: controller.acquisition.sessionName
                    onTextEdited: controller.acquisition.setSessionName(text)
                }

                ComboBox {
                    Layout.fillWidth: true
                    model: controller.acquisition.recordingLabels
                    editable: true
                    editText: controller.acquisition.recordingLabel
                    onEditTextChanged: controller.acquisition.setRecordingLabel(editText)
                }

                TextField {
                    Layout.fillWidth: true
                    placeholderText: "Marker 标签"
                    text: controller.acquisition.markerLabel
                    onTextEdited: controller.acquisition.setMarkerLabel(text)
                }

                TextField {
                    Layout.fillWidth: true
                    placeholderText: "区间标签"
                    text: controller.acquisition.segmentLabel
                    onTextEdited: controller.acquisition.setSegmentLabel(text)
                }
            }

            Label {
                Layout.fillWidth: true
                text: "输出目录：" + controller.acquisition.outputDirectory
                color: "#5f7288"
                wrapMode: Text.Wrap
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 10

                Button {
                    text: controller.acquisition.primaryActionText
                    highlighted: true
                    onClicked: controller.acquisition.toggleRecording()
                }

                Button {
                    text: "插入 Marker"
                    enabled: controller.acquisition.isRecording
                    onClicked: controller.acquisition.insertMarker()
                }

                Button {
                    text: controller.acquisition.toggleSegmentText
                    enabled: controller.acquisition.isRecording
                    onClicked: controller.acquisition.toggleSegment()
                }

                Button {
                    text: "清空区间"
                    enabled: controller.acquisition.isRecording
                             && controller.acquisition.isSegmentActive
                    onClicked: controller.acquisition.resetSegment()
                }
            }
        }

        Label {
            text: controller.previews.length > 0
                ? "实时预览"
                : "当前没有可预览的流"
            font.pixelSize: 22
            font.weight: Font.DemiBold
            color: "#102235"
        }

        Flow {
            Layout.fillWidth: true
            width: parent.width
            spacing: 14

            Repeater {
                model: controller.previews

                delegate: CardPanel {
                    width: root.availableWidth >= 1080
                        ? (root.availableWidth - 14) / 2
                        : root.availableWidth
                    title: modelData.displayName
                    subtitle: modelData.payloadType + " · " + modelData.sampleRateText

                    property var points: modelData.plotPoints || []
                    onPointsChanged: signalCanvas.requestPaint()

                    Label {
                        Layout.fillWidth: true
                        text: modelData.summaryText
                        color: "#5f7288"
                    }

                    Label {
                        Layout.fillWidth: true
                        text: modelData.channelSummary
                        color: "#8092a3"
                        wrapMode: Text.Wrap
                    }

                    Canvas {
                        id: signalCanvas
                        Layout.fillWidth: true
                        Layout.preferredHeight: modelData.payloadType === "signal" ? 180 : 0
                        visible: modelData.payloadType === "signal"

                        onPaint: {
                            const ctx = getContext("2d");
                            ctx.reset();
                            ctx.fillStyle = "#f4f8fc";
                            ctx.fillRect(0, 0, width, height);
                            if (!points || points.length < 2) {
                                return;
                            }
                            let minValue = points[0];
                            let maxValue = points[0];
                            for (let i = 1; i < points.length; i += 1) {
                                minValue = Math.min(minValue, points[i]);
                                maxValue = Math.max(maxValue, points[i]);
                            }
                            const span = Math.max(0.0001, maxValue - minValue);
                            ctx.strokeStyle = "#0f5cab";
                            ctx.lineWidth = 2;
                            ctx.beginPath();
                            for (let i = 0; i < points.length; i += 1) {
                                const x = (i / (points.length - 1)) * width;
                                const normalized = (points[i] - minValue) / span;
                                const y = height - normalized * height;
                                if (i === 0) {
                                    ctx.moveTo(x, y);
                                } else {
                                    ctx.lineTo(x, y);
                                }
                            }
                            ctx.stroke();
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: modelData.payloadType !== "signal" ? 220 : 0
                        visible: modelData.payloadType !== "signal"
                        radius: 16
                        color: "#f4f8fc"
                        border.width: 1
                        border.color: "#d8e4f0"

                        Image {
                            anchors.fill: parent
                            anchors.margins: 10
                            fillMode: Image.PreserveAspectFit
                            source: modelData.imageDataUrl
                            asynchronous: true
                            cache: false
                        }
                    }
                }
            }
        }
    }
}
