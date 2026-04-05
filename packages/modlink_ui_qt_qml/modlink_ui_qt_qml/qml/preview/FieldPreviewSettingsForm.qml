import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

ColumnLayout {
    id: root

    property var controller

    UiTokens { id: ui }

    function indexOfValue(items, value) {
        for (let i = 0; i < items.length; ++i) {
            const item = items[i];
            if ((item && item.value) === value || item === value) {
                return i;
            }
        }
        return 0;
    }

    spacing: 16

    Label {
        text: "图像渲染"
        font.pixelSize: 13
        font.weight: Font.DemiBold
        color: ui.textPrimary
    }

    GridLayout {
        Layout.fillWidth: true
        columns: 2
        rowSpacing: 8
        columnSpacing: 12

        Label { text: "插值"; color: ui.textSecondary; font.pixelSize: 12 }
        ComboBox {
            Layout.fillWidth: true
            textRole: "label"
            model: [
                { label: "Nearest", value: "nearest" },
                { label: "Bilinear", value: "bilinear" },
                { label: "Bicubic", value: "bicubic" }
            ]
            currentIndex: root.indexOfValue(model, controller ? controller.interpolation : "nearest")
            onActivated: if (controller) controller.setInterpolation(model[index].value)
        }

        Label { text: "变换"; color: ui.textSecondary; font.pixelSize: 12 }
        ComboBox {
            Layout.fillWidth: true
            textRole: "label"
            model: [
                { label: "无", value: "none" },
                { label: "水平翻转", value: "flip_horizontal" },
                { label: "垂直翻转", value: "flip_vertical" },
                { label: "旋转 90°", value: "rotate_90" },
                { label: "旋转 180°", value: "rotate_180" },
                { label: "旋转 270°", value: "rotate_270" }
            ]
            currentIndex: root.indexOfValue(model, controller ? controller.transformMode : "none")
            onActivated: if (controller) controller.setTransformMode(model[index].value)
        }

        Label { text: "数值范围"; color: ui.textSecondary; font.pixelSize: 12 }
        ComboBox {
            Layout.fillWidth: true
            textRole: "label"
            model: [
                { label: "自动", value: "auto" },
                { label: "0-1", value: "zero_to_one" },
                { label: "0-255", value: "zero_to_255" },
                { label: "手动", value: "manual" }
            ]
            currentIndex: root.indexOfValue(model, controller ? controller.valueRangeMode : "auto")
            onActivated: if (controller) controller.setValueRangeMode(model[index].value)
        }

        Label {
            text: "最小值"
            color: ui.textSecondary
            font.pixelSize: 12
            opacity: controller && controller.valueRangeMode === "manual" ? 1 : 0.4
        }
        TextField {
            Layout.fillWidth: true
            enabled: controller ? controller.valueRangeMode === "manual" : false
            text: controller ? String(controller.manualMin) : ""
            inputMethodHints: Qt.ImhFormattedNumbersOnly
            onEditingFinished: if (controller) controller.setManualMin(Number(text))
        }

        Label {
            text: "最大值"
            color: ui.textSecondary
            font.pixelSize: 12
            opacity: controller && controller.valueRangeMode === "manual" ? 1 : 0.4
        }
        TextField {
            Layout.fillWidth: true
            enabled: controller ? controller.valueRangeMode === "manual" : false
            text: controller ? String(controller.manualMax) : ""
            inputMethodHints: Qt.ImhFormattedNumbersOnly
            onEditingFinished: if (controller) controller.setManualMax(Number(text))
        }
    }
}
