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
        text: "布局与时间窗"
        font.pixelSize: 13
        font.weight: Font.DemiBold
        color: ui.textPrimary
    }

    GridLayout {
        Layout.fillWidth: true
        columns: 2
        rowSpacing: 8
        columnSpacing: 12

        Label { text: "时间窗"; color: ui.textSecondary; font.pixelSize: 12 }
        ComboBox {
            Layout.fillWidth: true
            model: [1, 2, 4, 8, 12, 20]
            currentIndex: root.indexOfValue(model, controller ? controller.windowSeconds : 8)
            onActivated: if (controller) controller.setWindowSeconds(Number(currentText))
        }

        Label { text: "布局"; color: ui.textSecondary; font.pixelSize: 12 }
        ComboBox {
            Layout.fillWidth: true
            textRole: "label"
            model: [
                { label: "独立轨道", value: "expanded" },
                { label: "叠加", value: "stacked" }
            ]
            currentIndex: root.indexOfValue(model, controller ? controller.layoutMode : "expanded")
            onActivated: if (controller) controller.setLayoutMode(model[index].value)
        }

        Label { text: "Y 轴范围"; color: ui.textSecondary; font.pixelSize: 12 }
        ComboBox {
            Layout.fillWidth: true
            textRole: "label"
            model: [
                { label: "自动", value: "auto" },
                { label: "手动", value: "manual" }
            ]
            currentIndex: root.indexOfValue(model, controller ? controller.yRangeMode : "auto")
            onActivated: if (controller) controller.setYRangeMode(model[index].value)
        }

        Label {
            text: "最小值"
            color: ui.textSecondary
            font.pixelSize: 12
            opacity: controller && controller.yRangeMode === "manual" ? 1 : 0.4
        }
        TextField {
            Layout.fillWidth: true
            enabled: controller ? controller.yRangeMode === "manual" : false
            text: controller ? String(controller.manualYMin) : ""
            inputMethodHints: Qt.ImhFormattedNumbersOnly
            onEditingFinished: if (controller) controller.setManualYMin(Number(text))
        }

        Label {
            text: "最大值"
            color: ui.textSecondary
            font.pixelSize: 12
            opacity: controller && controller.yRangeMode === "manual" ? 1 : 0.4
        }
        TextField {
            Layout.fillWidth: true
            enabled: controller ? controller.yRangeMode === "manual" : false
            text: controller ? String(controller.manualYMax) : ""
            inputMethodHints: Qt.ImhFormattedNumbersOnly
            onEditingFinished: if (controller) controller.setManualYMax(Number(text))
        }
    }

    Rectangle {
        Layout.fillWidth: true
        implicitHeight: 1
        color: ui.divider
    }

    Label {
        text: "基础滤波"
        font.pixelSize: 13
        font.weight: Font.DemiBold
        color: ui.textPrimary
    }

    GridLayout {
        Layout.fillWidth: true
        columns: 2
        rowSpacing: 8
        columnSpacing: 12

        Label { text: "滤波模式"; color: ui.textSecondary; font.pixelSize: 12 }
        ComboBox {
            Layout.fillWidth: true
            textRole: "label"
            model: [
                { label: "关闭", value: "none" },
                { label: "低通", value: "low_pass" },
                { label: "高通", value: "high_pass" },
                { label: "带通", value: "band_pass" },
                { label: "带阻", value: "band_stop" }
            ]
            currentIndex: root.indexOfValue(model, controller ? controller.filterMode : "none")
            onActivated: if (controller) controller.setFilterMode(model[index].value)
        }

        Label {
            text: "低截止 Hz"
            color: ui.textSecondary
            font.pixelSize: 12
            opacity: controller && controller.filterMode !== "none" ? 1 : 0.4
        }
        TextField {
            Layout.fillWidth: true
            enabled: controller ? controller.filterMode !== "none" : false
            text: controller ? String(controller.lowCutoffHz) : ""
            inputMethodHints: Qt.ImhFormattedNumbersOnly
            onEditingFinished: if (controller) controller.setLowCutoffHz(Number(text))
        }

        Label {
            text: "高截止 Hz"
            color: ui.textSecondary
            font.pixelSize: 12
            opacity: controller && controller.filterMode !== "none" ? 1 : 0.4
        }
        TextField {
            Layout.fillWidth: true
            enabled: controller ? controller.filterMode !== "none" : false
            text: controller ? String(controller.highCutoffHz) : ""
            inputMethodHints: Qt.ImhFormattedNumbersOnly
            onEditingFinished: if (controller) controller.setHighCutoffHz(Number(text))
        }
    }

    CheckBox {
        text: "启用工频陷波"
        checked: controller ? controller.notchEnabled : false
        onToggled: if (controller) controller.setNotchEnabled(checked)
    }
}
