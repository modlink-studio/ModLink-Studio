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
            text: "设置"
            font.pixelSize: 22
            font.weight: Font.DemiBold
            color: "#102235"
        }

        CardPanel {
            Layout.fillWidth: true
            title: "数据保存"
            subtitle: "新旧 UI 共用同一份 settings。"

            TextField {
                id: saveDirField
                Layout.fillWidth: true
                text: controller.saveDirectory
            }

            Button {
                text: "应用目录"
                onClicked: controller.setSaveDirectory(saveDirField.text)
            }
        }

        CardPanel {
            Layout.fillWidth: true
            title: "实时展示"
            subtitle: "控制基础预览的刷新节奏。"

            ComboBox {
                id: refreshRateCombo
                Layout.preferredWidth: 180
                model: controller.previewRateOptions
                currentIndex: controller.previewRateOptions.indexOf(controller.previewRefreshRateHz)
                onActivated: controller.setPreviewRefreshRateHz(Number(currentText))
            }
        }

        CardPanel {
            Layout.fillWidth: true
            title: "标签管理"
            subtitle: "录制和标注时复用这里的标签集合。"

            RowLayout {
                Layout.fillWidth: true

                TextField {
                    id: labelField
                    Layout.fillWidth: true
                    placeholderText: "输入新标签"
                }

                Button {
                    text: "添加"
                    onClicked: {
                        controller.addLabel(labelField.text)
                        labelField.clear()
                    }
                }
            }

            Flow {
                Layout.fillWidth: true
                spacing: 8

                Repeater {
                    model: controller.labels

                    delegate: TagChip {
                        text: modelData
                        onRemoveRequested: controller.removeLabel(modelData)
                    }
                }
            }
        }
    }
}
