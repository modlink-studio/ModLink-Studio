"""Internationalization support for scaffold CLI."""

from __future__ import annotations

from typing import Literal

Language = Literal["en", "zh"]


COPY_EN = {
    # App title
    "app_title": "ModLink Plugin Scaffold",
    # Section names
    "identity_section": "Identity",
    "connection_section": "Connection",
    "driver_section": "Driver",
    "streams_section": "Streams",
    "dependencies_section": "Dependencies",
    # Section descriptions
    "identity_description": "Plugin name, display name, and device ID",
    "connection_description": "Connection providers and data arrival mode",
    "driver_description": "Driver kind (Driver or LoopDriver)",
    "streams_description": "Data streams configuration",
    "dependencies_description": "Additional dependencies",
    # Labels
    "plugin_name_label": "Plugin name",
    "display_name_label": "Display name",
    "device_id_label": "Device ID",
    "providers_label": "Providers",
    "data_arrival_label": "Data arrival",
    "driver_kind_label": "Driver kind",
    "dependencies_label": "Dependencies",
    "stream_key_label": "Stream key",
    "stream_name_label": "Display name",
    "payload_type_label": "Payload type",
    "sample_rate_label": "Sample rate (Hz)",
    "chunk_size_label": "Chunk size",
    "channel_count_label": "Channel count",
    "channel_names_label": "Channel names",
    "unit_label": "Unit",
    "raster_length_label": "Raster length",
    "field_height_label": "Field height",
    "field_width_label": "Field width",
    "video_height_label": "Video height",
    "video_width_label": "Video width",
    "stream_count_label": "Stream count",
    # Prompts
    "plugin_name_prompt": "Enter plugin name (e.g., my_device)",
    "display_name_prompt": "Enter display name",
    "device_id_prompt": "Enter device ID (e.g., my_device.01)",
    "providers_prompt": "Enter providers (comma-separated, e.g., serial, tcp)",
    "data_arrival_prompt": "Select data arrival mode",
    "driver_kind_prompt": "Select driver kind",
    "dependencies_prompt": "Enter additional dependencies (comma-separated)",
    "add_stream_prompt": "Configure stream #{index}",
    "stream_key_prompt": "Stream key",
    "stream_name_prompt": "Stream display name",
    "payload_type_prompt": "Payload type",
    "add_more_streams_prompt": "Add another stream?",
    "confirm_generate_prompt": "Generate project?",
    "overwrite_prompt": "Directory exists. Overwrite?",
    # Choices
    "data_arrival_choices": ["push", "poll", "unsure"],
    "driver_kind_choices": ["driver", "loop"],
    "payload_type_choices": ["signal", "raster", "field", "video"],
    # Data arrival descriptions
    "push_description": "Device pushes data (callback/event-driven)",
    "poll_description": "Host polls device (periodic read)",
    "unsure_description": "Not sure yet",
    # Driver kind descriptions
    "driver_description": "Callback-based (Device pushes data)",
    "loop_description": "Poll-based (Host reads periodically)",
    # Payload type descriptions
    "signal_description": "Time-series signal (channels x samples)",
    "raster_description": "1D raster scan (channels x samples x length)",
    "field_description": "2D field data (channels x samples x height x width)",
    "video_description": "Video frames (channels x samples x height x width)",
    # Errors
    "plugin_name_error": "Plugin name must be a valid identifier",
    "device_id_error": "Device ID must match pattern: name.01 (lowercase, digits)",
    "providers_error": "At least one provider is required",
    "streams_required_error": "At least one stream is required",
    "stream_key_error": "Stream key must be a valid identifier",
    "positive_int_error": "Must be a positive integer",
    "positive_float_error": "Must be a positive number",
    "channel_names_error": "Channel names are required",
    "channel_names_count_error": "Channel names count must match channel count",
    "output_exists_error": "Output directory already exists",
    # Status
    "ready_short": "Ready",
    "issues_short": "issues",
    "generating": "Generating...",
    "generation_succeeded": "Generation succeeded!",
    "overwrite_cancelled": "Overwrite cancelled",
    "validation_blocked": "Validation blocked",
    "invalid_preview_placeholder": "[validation errors]",
    "default_stream_name": "Stream",
    # Summary
    "summary_title": "Driver Summary",
    "invalid_summary_message": "Please fix validation errors",
    # Reasons
    "reason_push_driver": "Device pushes data asynchronously; use Driver for callbacks.",
    "reason_push_loop": "LoopDriver can work but Driver is preferred for push mode.",
    "reason_poll_loop": "Host polls device periodically; LoopDriver simplifies timing.",
    "reason_poll_driver": "Driver can work but LoopDriver is preferred for poll mode.",
    "reason_unsure_driver": "Default choice; switch to LoopDriver if you need polling.",
    "reason_unsure_loop": "Good for periodic reads; switch to Driver for callbacks.",
    # Result
    "result_title": "Generated Successfully!",
    "result_files": "Files created:",
    "result_commands": "Next steps:",
    "install_command": "Install: python -m pip install -e .",
    "test_command": "Test: python -m pytest",
    "run_command": "Run: python -m modlink_studio",
    # Data arrival summary
    "data_arrival_summary": {
        "push": "Push (event-driven)",
        "poll": "Poll (periodic read)",
        "unsure": "Unsure",
    },
}


COPY_ZH = {
    # App title
    "app_title": "ModLink Plugin 脚手架",
    # Section names
    "identity_section": "标识",
    "connection_section": "连接",
    "driver_section": "Driver",
    "streams_section": "数据流",
    "dependencies_section": "依赖",
    # Section descriptions
    "identity_description": "插件名称、显示名称和设备 ID",
    "connection_description": "连接提供者和数据到达模式",
    "driver_description": "Driver 类型 (Driver 或 LoopDriver)",
    "streams_description": "数据流配置",
    "dependencies_description": "额外依赖",
    # Labels
    "plugin_name_label": "插件名称",
    "display_name_label": "显示名称",
    "device_id_label": "设备 ID",
    "providers_label": "提供者",
    "data_arrival_label": "数据到达",
    "driver_kind_label": "Driver 类型",
    "dependencies_label": "依赖",
    "stream_key_label": "流键名",
    "stream_name_label": "显示名称",
    "payload_type_label": "Payload 类型",
    "sample_rate_label": "采样率 (Hz)",
    "chunk_size_label": "块大小",
    "channel_count_label": "通道数",
    "channel_names_label": "通道名称",
    "unit_label": "单位",
    "raster_length_label": "Raster 长度",
    "field_height_label": "Field 高度",
    "field_width_label": "Field 宽度",
    "video_height_label": "视频高度",
    "video_width_label": "视频宽度",
    "stream_count_label": "数据流数量",
    # Prompts
    "plugin_name_prompt": "输入插件名称 (如 my_device)",
    "display_name_prompt": "输入显示名称",
    "device_id_prompt": "输入设备 ID (如 my_device.01)",
    "providers_prompt": "输入提供者 (逗号分隔，如 serial, tcp)",
    "data_arrival_prompt": "选择数据到达模式",
    "driver_kind_prompt": "选择 Driver 类型",
    "dependencies_prompt": "输入额外依赖 (逗号分隔)",
    "add_stream_prompt": "配置数据流 #{index}",
    "stream_key_prompt": "流键名",
    "stream_name_prompt": "流显示名称",
    "payload_type_prompt": "Payload 类型",
    "add_more_streams_prompt": "添加更多数据流？",
    "confirm_generate_prompt": "生成项目？",
    "overwrite_prompt": "目录已存在。覆盖？",
    # Choices (same as EN)
    "data_arrival_choices": ["push", "poll", "unsure"],
    "driver_kind_choices": ["driver", "loop"],
    "payload_type_choices": ["signal", "raster", "field", "video"],
    # Data arrival descriptions
    "push_description": "设备推送数据 (回调/事件驱动)",
    "poll_description": "主机轮询设备 (周期读取)",
    "unsure_description": "尚未确定",
    # Driver kind descriptions
    "driver_description": "回调驱动 (设备推送数据)",
    "loop_description": "轮询驱动 (主机周期读取)",
    # Payload type descriptions
    "signal_description": "时间序列信号 (通道 x 样本)",
    "raster_description": "1D 光栅扫描 (通道 x 样本 x 长度)",
    "field_description": "2D 场数据 (通道 x 样本 x 高 x 宽)",
    "video_description": "视频帧 (通道 x 样本 x 高 x 宽)",
    # Errors
    "plugin_name_error": "插件名称必须是有效标识符",
    "device_id_error": "设备 ID 必须匹配格式: name.01 (小写字母, 数字)",
    "providers_error": "至少需要一个提供者",
    "streams_required_error": "至少需要一个数据流",
    "stream_key_error": "流键名必须是有效标识符",
    "positive_int_error": "必须是正整数",
    "positive_float_error": "必须是正数",
    "channel_names_error": "通道名称是必需的",
    "channel_names_count_error": "通道名称数量必须与通道数匹配",
    "output_exists_error": "输出目录已存在",
    # Status
    "ready_short": "就绪",
    "issues_short": "个问题",
    "generating": "生成中...",
    "generation_succeeded": "生成成功！",
    "overwrite_cancelled": "覆盖已取消",
    "validation_blocked": "验证受阻",
    "invalid_preview_placeholder": "[验证错误]",
    "default_stream_name": "数据流",
    # Summary
    "summary_title": "Driver 概要",
    "invalid_summary_message": "请修复验证错误",
    # Reasons
    "reason_push_driver": "设备异步推送数据；使用 Driver 处理回调。",
    "reason_push_loop": "LoopDriver 可用，但推荐 Driver 用于推送模式。",
    "reason_poll_loop": "主机周期轮询设备；LoopDriver 简化定时控制。",
    "reason_poll_driver": "Driver 可用，但推荐 LoopDriver 用于轮询模式。",
    "reason_unsure_driver": "默认选择；需要轮询时可切换到 LoopDriver。",
    "reason_unsure_loop": "适合周期读取；需要回调时可切换到 Driver。",
    # Result
    "result_title": "生成成功！",
    "result_files": "已创建文件：",
    "result_commands": "下一步：",
    "install_command": "安装: python -m pip install -e .",
    "test_command": "测试: python -m pytest",
    "run_command": "运行: python -m modlink_studio",
    # Data arrival summary
    "data_arrival_summary": {
        "push": "推送 (事件驱动)",
        "poll": "轮询 (周期读取)",
        "unsure": "不确定",
    },
}


def get_copy(language: Language) -> dict[str, str | list[str]]:
    """Get copy dictionary for the specified language."""
    return COPY_ZH if language == "zh" else COPY_EN


def get_label(key: str, language: Language) -> str:
    """Get a label for the specified key."""
    copy = get_copy(language)
    value = copy.get(key)
    if isinstance(value, str):
        return value
    return key


def get_description(key: str, language: Language) -> str:
    """Get a description for the specified key."""
    copy = get_copy(language)
    return copy.get(key, "") if isinstance(copy.get(key), str) else ""


# Ordered choices for cycling
DATA_ARRIVAL_ORDER = ["push", "poll", "unsure"]
DRIVER_KIND_ORDER = ["driver", "loop"]
PAYLOAD_TYPE_ORDER = ["signal", "raster", "field", "video"]