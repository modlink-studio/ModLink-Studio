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
            text: "设置"
            font.pixelSize: 20
            font.weight: Font.DemiBold
            color: palette.windowText
            Layout.leftMargin: 16
            Layout.topMargin: 16
        }

        CardPanel {
            Layout.fillWidth: true
            Layout.leftMargin: 16
            Layout.rightMargin: 16
            title: "数据保存"
            subtitle: "配置采集数据的保存路径。"

            RowLayout {
                Layout.fillWidth: true
                spacing: 8

                TextField {
                    id: saveDirField
                    Layout.fillWidth: true
                    text: controller ? controller.saveDirectory : ""
                    placeholderText: "保存目录路径"
                }

                Button {
                    text: "应用"
                    highlighted: true
                    onClicked: { if (controller) controller.setSaveDirectory(saveDirField.text); }
                }
            }
        }

        CardPanel {
            Layout.fillWidth: true
            Layout.leftMargin: 16
            Layout.rightMargin: 16
            title: "实时展示"
            subtitle: "控制预览的刷新频率。"

            RowLayout {
                Layout.fillWidth: true
                spacing: 8

                Label {
                    text: "刷新率"
                    color: palette.windowText
                }

                ComboBox {
                    Layout.preferredWidth: 160
                    model: controller ? controller.previewRateOptions : []
                    currentIndex: (controller && controller.previewRateOptions) ? controller.previewRateOptions.indexOf(controller.previewRefreshRateHz) : -1
                    onActivated: { if (controller) controller.setPreviewRefreshRateHz(Number(currentText)); }

                    delegate: ItemDelegate {
                        text: modelData + " Hz"
                        width: parent.width
                    }
                }
            }
        }

        CardPanel {
            Layout.fillWidth: true
            Layout.leftMargin: 16
            Layout.rightMargin: 16
            title: "标签管理"
            subtitle: "录制和标注时复用的标签集合。"

            RowLayout {
                Layout.fillWidth: true
                spacing: 8

                TextField {
                    id: labelField
                    Layout.fillWidth: true
                    placeholderText: "输入新标签"
                    onAccepted: {
                        if (controller) controller.addLabel(labelField.text);
                        labelField.clear();
                    }
                }

                Button {
                    text: "添加"
                    highlighted: true
                    onClicked: {
                        if (controller) controller.addLabel(labelField.text);
                        labelField.clear();
                    }
                }
            }

            Flow {
                Layout.fillWidth: true
                spacing: 6

                Repeater {
                    model: controller ? controller.labels : []

                    delegate: TagChip {
                        text: modelData
                        onRemoveRequested: { if (controller) controller.removeLabel(modelData); }
                    }
                }
            }
        }

        Item { Layout.fillHeight: true }
    }
}
