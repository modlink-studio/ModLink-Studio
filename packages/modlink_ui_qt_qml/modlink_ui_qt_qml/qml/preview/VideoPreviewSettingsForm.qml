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
        text: "视频渲染"
        font.pixelSize: 13
        font.weight: Font.DemiBold
        color: ui.textPrimary
    }

    GridLayout {
        Layout.fillWidth: true
        columns: 2
        rowSpacing: 8
        columnSpacing: 12

        Label { text: "颜色格式"; color: ui.textSecondary; font.pixelSize: 12 }
        ComboBox {
            Layout.fillWidth: true
            textRole: "label"
            model: [
                { label: "RGB", value: "rgb" },
                { label: "BGR", value: "bgr" },
                { label: "Gray", value: "gray" },
                { label: "YUV", value: "yuv" }
            ]
            currentIndex: root.indexOfValue(model, controller ? controller.colorFormat : "rgb")
            onActivated: if (controller) controller.setColorFormat(model[index].value)
        }

        Label { text: "缩放"; color: ui.textSecondary; font.pixelSize: 12 }
        ComboBox {
            Layout.fillWidth: true
            textRole: "label"
            model: [
                { label: "Fit", value: "fit" },
                { label: "Fill", value: "fill" }
            ]
            currentIndex: root.indexOfValue(model, controller ? controller.scaleMode : "fit")
            onActivated: if (controller) controller.setScaleMode(model[index].value)
        }

        Label { text: "纵横比"; color: ui.textSecondary; font.pixelSize: 12 }
        ComboBox {
            Layout.fillWidth: true
            textRole: "label"
            model: [
                { label: "保持", value: "keep" },
                { label: "拉伸", value: "stretch" }
            ]
            currentIndex: root.indexOfValue(model, controller ? controller.aspectMode : "keep")
            onActivated: if (controller) controller.setAspectMode(model[index].value)
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
    }
}
