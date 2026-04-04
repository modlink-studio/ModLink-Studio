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
            title: "设置"
            subtitle: "集中管理保存目录、预览刷新率和录制标签。"
        }

        CardPanel {
            Layout.fillWidth: true
            title: "数据保存"
            subtitle: "配置采集数据的默认保存路径。"

            RowLayout {
                Layout.fillWidth: true
                spacing: 10

                TextField {
                    id: saveDirField
                    Layout.fillWidth: true
                    Layout.minimumWidth: 360
                    text: controller ? controller.saveDirectory : ""
                    placeholderText: "保存目录路径"
                }

                Button {
                    text: "应用"
                    highlighted: true
                    onClicked: {
                        if (controller) controller.setSaveDirectory(saveDirField.text);
                    }
                }
            }
        }

        CardPanel {
            Layout.fillWidth: true
            title: "实时展示"
            subtitle: "控制主页面预览的刷新频率。"

            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                Label {
                    text: "刷新率"
                    font.pixelSize: 13
                    color: ui.textSecondary
                }

                ComboBox {
                    Layout.preferredWidth: 180
                    model: controller ? controller.previewRateOptions : []
                    currentIndex: (controller && controller.previewRateOptions)
                        ? controller.previewRateOptions.indexOf(controller.previewRefreshRateHz)
                        : -1
                    onActivated: {
                        if (controller) controller.setPreviewRefreshRateHz(Number(currentText));
                    }
                }
            }
        }

        CardPanel {
            Layout.fillWidth: true
            title: "标签管理"
            subtitle: "录制和标注时复用的标签集合。"

            RowLayout {
                Layout.fillWidth: true
                spacing: 10

                TextField {
                    id: labelField
                    Layout.fillWidth: true
                    Layout.minimumWidth: 300
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
                spacing: 8

                Repeater {
                    model: controller ? controller.labels : []

                    delegate: TagChip {
                        text: modelData
                        onRemoveRequested: {
                            if (controller) controller.removeLabel(modelData);
                        }
                    }
                }
            }
        }

        Item { Layout.fillHeight: true }
    }
}
