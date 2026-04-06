import type { DataArrival, DriverKind, Language, PayloadType, SectionId } from "./types.js";

type Copy = {
  appTitle: string;
  appSubtitle: string;
  helpLine: string;
  previewHeader: string;
  previewTruncated: string;
  readyToGenerate: string;
  cannotGenerate: string;
  generateAction: string;
  quitAction: string;
  confirmOverwriteTitle: string;
  confirmOverwriteBody: string;
  confirmOverwriteCancel: string;
  confirmOverwriteConfirm: string;
  completionTitle: string;
  completionHint: string;
  locationLabel: string;
  controlsLabel: string;
  editingLabel: string;
  currentSectionLabel: string;
  currentPreviewLabel: string;
  identitySection: string;
  connectionSection: string;
  driverSection: string;
  streamsSection: string;
  dependenciesSection: string;
  pluginNameLabel: string;
  displayNameLabel: string;
  deviceIdLabel: string;
  providersLabel: string;
  dataArrivalLabel: string;
  driverKindLabel: string;
  recommendedDriverLabel: string;
  dependenciesLabel: string;
  selectedStreamLabel: string;
  streamAddAction: string;
  streamDuplicateAction: string;
  streamDeleteAction: string;
  streamMoveUpAction: string;
  streamMoveDownAction: string;
  streamModalityLabel: string;
  streamDisplayNameLabel: string;
  streamPayloadLabel: string;
  streamSampleRateLabel: string;
  streamChunkSizeLabel: string;
  streamChannelCountLabel: string;
  streamChannelNamesLabel: string;
  streamUnitLabel: string;
  streamRasterLengthLabel: string;
  streamFieldHeightLabel: string;
  streamFieldWidthLabel: string;
  streamVideoHeightLabel: string;
  streamVideoWidthLabel: string;
  choiceSwitchHint: string;
  streamListTitle: string;
  streamListDescription: string;
  streamActionsDescription: string;
  streamDetailsTitle: string;
  streamBasicGroupTitle: string;
  streamBasicGroupDescription: string;
  streamTimingGroupTitle: string;
  streamTimingGroupDescription: string;
  streamPayloadGroupTitle: string;
  streamPayloadGroupDescription: string;
  sections: Record<SectionId, string>;
  sectionDescriptions: Record<SectionId, string>;
  rowDescriptions: Record<string, string>;
  payloadOptions: Record<PayloadType, string>;
  dataArrivalOptions: Record<DataArrival, string>;
  dataArrivalSummaryOptions: Record<DataArrival, string>;
  driverKindOptions: Record<DriverKind, string>;
  invalidPreviewPlaceholder: string;
  validationErrorsHeader: string;
  defaultStreamName: string;
  generatedFilesLabel: string;
  commandsLabel: string;
  summaryTitle: string;
  statusPrefix: string;
  outputDirLabel: string;
  streamCountLabel: string;
  payloadMixLabel: string;
  footerEditHint: string;
  footerIdleHint: string;
  readyShort: string;
  issuesShort: string;
  invalidSummaryMessage: string;
  pluginNameError: string;
  deviceIdError: string;
  providersError: string;
  modalityError: string;
  positiveFloatError: string;
  positiveIntError: string;
  channelNamesError: string;
  signalChannelNamesCountError: string;
  streamsRequiredError: string;
  validationBlocked: string;
  overwriteCancelled: string;
  generationSucceeded: string;
  outputExists: string;
  reasonPushDriver: string;
  reasonPushLoop: string;
  reasonPollDriver: string;
  reasonPollLoop: string;
  reasonUnsureDriver: string;
  reasonUnsureLoop: string;
};

const en: Copy = {
  appTitle: "ModLink Plugin Scaffold",
  appSubtitle: "React + Ink developer tool for Python driver plugins",
  helpLine:
    "Tab: next section | Up/Down: rows | Left/Right: choices | Enter: edit or run | g: generate | q: quit",
  previewHeader: "Preview",
  previewTruncated: "Preview truncated to fit the current terminal height.",
  readyToGenerate: "Draft is valid and ready to generate.",
  cannotGenerate: "Fix the highlighted validation issues before generating.",
  generateAction: "Generate scaffold",
  quitAction: "Quit",
  confirmOverwriteTitle: "Overwrite existing project?",
  confirmOverwriteBody: "The target directory already exists:",
  confirmOverwriteCancel: "Cancel",
  confirmOverwriteConfirm: "Overwrite",
  completionTitle: "Scaffold generated",
  completionHint: "Press Enter, Esc, or q to exit.",
  locationLabel: "Location",
  controlsLabel: "Controls",
  editingLabel: "Edit",
  currentSectionLabel: "Section",
  currentPreviewLabel: "Preview tab",
  identitySection: "Identity",
  connectionSection: "Connection",
  driverSection: "Driver Type",
  streamsSection: "Streams",
  dependenciesSection: "Dependencies",
  pluginNameLabel: "Plugin name",
  displayNameLabel: "Display name",
  deviceIdLabel: "Device ID",
  providersLabel: "Providers",
  dataArrivalLabel: "Data arrival",
  driverKindLabel: "Driver base class",
  recommendedDriverLabel: "Recommended",
  dependenciesLabel: "Extra dependencies",
  selectedStreamLabel: "Current stream",
  streamAddAction: "Add stream",
  streamDuplicateAction: "Duplicate stream",
  streamDeleteAction: "Delete stream",
  streamMoveUpAction: "Move stream up",
  streamMoveDownAction: "Move stream down",
  streamModalityLabel: "Modality",
  streamDisplayNameLabel: "Stream display name",
  streamPayloadLabel: "Payload type",
  streamSampleRateLabel: "Sample rate / fps",
  streamChunkSizeLabel: "Chunk size",
  streamChannelCountLabel: "Channel count",
  streamChannelNamesLabel: "Channel names",
  streamUnitLabel: "Unit",
  streamRasterLengthLabel: "Raster line length",
  streamFieldHeightLabel: "Field height",
  streamFieldWidthLabel: "Field width",
  streamVideoHeightLabel: "Frame height",
  streamVideoWidthLabel: "Frame width",
  choiceSwitchHint: "[←/→ switch]",
  streamListTitle: "Streams",
  streamListDescription: "Select which stream to edit.",
  streamActionsDescription: "Use Enter to add or delete.",
  streamDetailsTitle: "Current stream details",
  streamBasicGroupTitle: "Basics",
  streamBasicGroupDescription: "Name the stream and choose its payload type.",
  streamTimingGroupTitle: "Timing",
  streamTimingGroupDescription: "Set the nominal rate and chunk size.",
  streamPayloadGroupTitle: "Payload",
  streamPayloadGroupDescription: "Fill in the fields required by the selected payload type.",
  sections: {
    identity: "Identity",
    connection: "Connection",
    driver: "Driver Type",
    streams: "Streams",
    dependencies: "Dependencies",
  },
  sectionDescriptions: {
    identity: "Define the generated package name, device label, and stable device ID.",
    connection: "Describe how the host discovers the plugin and how the device produces data.",
    driver: "Choose the runtime base class that best matches the device behavior.",
    streams: "Describe every stream the driver will publish, including shape and metadata.",
    dependencies: "List extra Python packages that the generated driver project should install.",
  },
  rowDescriptions: {
    "identity.pluginName": "Python package name used for the plugin folder and entry point key.",
    "identity.displayName": "Human-readable device name shown in the host UI.",
    "identity.deviceId": "Stable identifier used by descriptors, recordings, and saved sessions.",
    "connection.providersText": "Comma-separated provider tokens, such as serial or ble.",
    "connection.dataArrival":
      "Whether the SDK pushes frames into your code or your code polls on its own loop.",
    "driver.driverKind":
      "Choose Driver for push-style runtimes, or LoopDriver for poll-style runtimes.",
    "dependencies.dependenciesText":
      "Extra pip dependencies to include in the generated pyproject.toml.",
    "streams.select": "Select which stream definition is currently shown on the right.",
    "streams.add": "Append a brand-new stream using the default values for its payload type.",
    "streams.delete": "Remove the selected stream from the generated driver project.",
    "streams.modality": "Short stream key, for example eeg, imu, camera, or temperature.",
    "streams.displayName": "Visible stream name shown in the host UI and metadata.",
    "streams.payloadType": "Shape family for the emitted payload: signal, raster, field, or video.",
    "streams.sampleRateHz": "Nominal sample rate or frame rate written into the stream descriptor.",
    "streams.chunkSize": "How many samples or frames each emitted chunk should contain.",
    "streams.channelCount": "Number of logical channels carried by this stream.",
    "streams.channelNames": "Comma-separated channel labels in descriptor order.",
    "streams.unit": "Measurement unit, such as V, m/s^2, or degC.",
    "streams.rasterLength": "Samples per raster line for raster payloads.",
    "streams.fieldHeight": "Spatial height for field payloads.",
    "streams.fieldWidth": "Spatial width for field payloads.",
    "streams.videoHeight": "Frame height in pixels for video payloads.",
    "streams.videoWidth": "Frame width in pixels for video payloads.",
  },
  payloadOptions: {
    signal: "signal",
    raster: "raster",
    field: "field",
    video: "video",
  },
  dataArrivalOptions: {
    push: "SDK pushes data into your code",
    poll: "Your code polls on its own loop",
    unsure: "You are still not sure",
  },
  dataArrivalSummaryOptions: {
    push: "SDK push",
    poll: "Self polling",
    unsure: "Unclear",
  },
  driverKindOptions: {
    driver: "Driver",
    loop: "LoopDriver",
  },
  invalidPreviewPlaceholder: "Preview is unavailable until the draft passes validation.",
  validationErrorsHeader: "Validation errors",
  defaultStreamName: "Stream",
  generatedFilesLabel: "Generated files",
  commandsLabel: "Next commands",
  summaryTitle: "Scaffold summary",
  statusPrefix: "Status",
  outputDirLabel: "Output dir",
  streamCountLabel: "Streams",
  payloadMixLabel: "Payload mix",
  footerEditHint: "Enter submit | Esc cancel | Backspace delete",
  footerIdleHint: "[tab] section  [↑/↓] move  [←/→] switch  [enter] edit  [g] generate  [q] quit",
  readyShort: "ready",
  issuesShort: "issues",
  invalidSummaryMessage: "Complete the required fields to unlock the scaffold summary.",
  pluginNameError: "Plugin name must contain at least one letter or number.",
  deviceIdError: "Device ID must match name.XX, for example my_driver.01.",
  providersError: "Provide at least one provider token.",
  modalityError: "Modality must contain at least one letter or number.",
  positiveFloatError: "Enter a positive number.",
  positiveIntError: "Enter a positive integer.",
  channelNamesError: "Provide at least one channel name.",
  signalChannelNamesCountError: "Signal channel names must match the channel count.",
  streamsRequiredError: "At least one stream is required.",
  validationBlocked: "Generation is blocked until the draft passes validation.",
  overwriteCancelled: "Overwrite cancelled.",
  generationSucceeded: "Scaffold generated successfully.",
  outputExists: "Target directory already exists.",
  reasonPushDriver: "The SDK pushes data into your code, so Driver is the natural default.",
  reasonPushLoop:
    "The SDK pushes data, but LoopDriver was kept manually for a polling-style design.",
  reasonPollDriver:
    "Your code polls on its own schedule, but Driver is still valid if you want to own the lifecycle.",
  reasonPollLoop:
    "Your code polls on its own loop or timer, so LoopDriver is the recommended base class.",
  reasonUnsureDriver:
    "Driver is the safer starting point until the device runtime pattern is clear.",
  reasonUnsureLoop:
    "LoopDriver was kept manually even though the runtime pattern is still uncertain.",
};

const zh: Copy = {
  appTitle: "ModLink 插件脚手架",
  appSubtitle: "基于 React + Ink 的 Python driver 开发工具",
  helpLine: "Tab: 下一分区 | 上下: 行切换 | 左右: 切换选项 | Enter: 编辑或执行 | g: 生成 | q: 退出",
  previewHeader: "预览",
  previewTruncated: "预览内容已按当前终端高度截断。",
  readyToGenerate: "当前草稿已通过校验，可以生成。",
  cannotGenerate: "请先修正高亮的校验问题。",
  generateAction: "生成脚手架",
  quitAction: "退出",
  confirmOverwriteTitle: "要覆盖已有项目吗？",
  confirmOverwriteBody: "目标目录已经存在：",
  confirmOverwriteCancel: "取消",
  confirmOverwriteConfirm: "覆盖",
  completionTitle: "脚手架已生成",
  completionHint: "按 Enter、Esc 或 q 退出。",
  locationLabel: "位置",
  controlsLabel: "操作",
  editingLabel: "编辑",
  currentSectionLabel: "当前分区",
  currentPreviewLabel: "当前预览",
  identitySection: "基本信息",
  connectionSection: "连接方式",
  driverSection: "Driver 类型",
  streamsSection: "Streams",
  dependenciesSection: "依赖",
  pluginNameLabel: "插件名",
  displayNameLabel: "显示名",
  deviceIdLabel: "Device ID",
  providersLabel: "Providers",
  dataArrivalLabel: "数据到达方式",
  driverKindLabel: "Driver 基类",
  recommendedDriverLabel: "推荐",
  dependenciesLabel: "额外依赖",
  selectedStreamLabel: "当前 stream",
  streamAddAction: "新增 stream",
  streamDuplicateAction: "复制 stream",
  streamDeleteAction: "删除 stream",
  streamMoveUpAction: "上移 stream",
  streamMoveDownAction: "下移 stream",
  streamModalityLabel: "Modality",
  streamDisplayNameLabel: "Stream 显示名",
  streamPayloadLabel: "Payload type",
  streamSampleRateLabel: "采样率 / 帧率",
  streamChunkSizeLabel: "Chunk 大小",
  streamChannelCountLabel: "Channel 数量",
  streamChannelNamesLabel: "Channel 名称",
  streamUnitLabel: "单位",
  streamRasterLengthLabel: "Raster line 长度",
  streamFieldHeightLabel: "Field 高度",
  streamFieldWidthLabel: "Field 宽度",
  streamVideoHeightLabel: "帧高度",
  streamVideoWidthLabel: "帧宽度",
  choiceSwitchHint: "[←/→ 切换]",
  streamListTitle: "已有 streams",
  streamListDescription: "选择要编辑的 stream。",
  streamActionsDescription: "按 Enter 新增或删除。",
  streamDetailsTitle: "当前 stream 详情",
  streamBasicGroupTitle: "基础",
  streamBasicGroupDescription: "设置 stream 名称、显示名和 payload 类型。",
  streamTimingGroupTitle: "采样",
  streamTimingGroupDescription: "设置采样率/帧率和每个 chunk 的大小。",
  streamPayloadGroupTitle: "Payload",
  streamPayloadGroupDescription: "根据 payload 类型填写对应字段。",
  sections: {
    identity: "基本信息",
    connection: "连接方式",
    driver: "Driver 类型",
    streams: "Streams",
    dependencies: "依赖",
  },
  sectionDescriptions: {
    identity: "定义生成项目的包名、显示名和稳定的 Device ID。",
    connection: "说明宿主如何发现插件，以及设备数据是如何到达驱动的。",
    driver: "选择最适合当前设备运行方式的 Driver 基类。",
    streams: "配置驱动会发布的每一个 stream，包括形状和元数据。",
    dependencies: "列出生成后的 Python driver 项目需要额外安装的依赖。",
  },
  rowDescriptions: {
    "identity.pluginName": "Python 包名，会用于插件目录名和 entry point 键名。",
    "identity.displayName": "面向用户显示的设备名称，会出现在宿主界面里。",
    "identity.deviceId": "稳定的设备标识，会写入 descriptor、录制文件和 session 元数据。",
    "connection.providersText": "用逗号分隔的 provider token，例如 serial、ble。",
    "connection.dataArrival": "描述是 SDK 主动推送数据，还是你的代码自己轮询采集。",
    "driver.driverKind": "push 型通常选 Driver，轮询或定时器模型通常选 LoopDriver。",
    "dependencies.dependenciesText": "额外的 pip 依赖，会写进生成项目的 pyproject.toml。",
    "streams.select": "选择当前正在右侧编辑的 stream 定义。",
    "streams.add": "按当前默认配置新增一个 stream。",
    "streams.delete": "从生成项目里移除当前选中的 stream。",
    "streams.modality": "简短的 stream key，例如 eeg、imu、camera、temperature。",
    "streams.displayName": "显示在宿主界面和元数据里的 stream 名称。",
    "streams.payloadType": "输出数据的形状类型：signal、raster、field 或 video。",
    "streams.sampleRateHz": "写入 stream descriptor 的标称采样率或帧率。",
    "streams.chunkSize": "每次发出一个 chunk 时包含多少样本或帧。",
    "streams.channelCount": "当前 stream 包含的逻辑 channel 数量。",
    "streams.channelNames": "按 descriptor 顺序填写的 channel 名称，使用逗号分隔。",
    "streams.unit": "测量单位，例如 V、m/s^2 或 degC。",
    "streams.rasterLength": "raster payload 每一行包含的样本数。",
    "streams.fieldHeight": "field payload 的空间高度。",
    "streams.fieldWidth": "field payload 的空间宽度。",
    "streams.videoHeight": "video payload 的帧高，单位像素。",
    "streams.videoWidth": "video payload 的帧宽，单位像素。",
  },
  payloadOptions: {
    signal: "signal",
    raster: "raster",
    field: "field",
    video: "video",
  },
  dataArrivalOptions: {
    push: "SDK 主动把数据推到你的代码里",
    poll: "你的代码自己轮询设备",
    unsure: "现在还不确定",
  },
  dataArrivalSummaryOptions: {
    push: "SDK 推送",
    poll: "主动轮询",
    unsure: "暂未确定",
  },
  driverKindOptions: {
    driver: "Driver",
    loop: "LoopDriver",
  },
  invalidPreviewPlaceholder: "当前草稿还未通过校验，因此暂时无法预览生成文件。",
  validationErrorsHeader: "校验问题",
  defaultStreamName: "Stream",
  generatedFilesLabel: "生成的文件",
  commandsLabel: "后续命令",
  summaryTitle: "脚手架摘要",
  statusPrefix: "状态",
  outputDirLabel: "输出目录",
  streamCountLabel: "Streams",
  payloadMixLabel: "Payload 组合",
  footerEditHint: "Enter 提交 | Esc 取消 | Backspace 删除",
  footerIdleHint: "[tab] 分区  [↑/↓] 移动  [←/→] 切换  [enter] 编辑  [g] 生成  [q] 退出",
  readyShort: "可生成",
  issuesShort: "问题",
  invalidSummaryMessage: "先补齐必填字段，顶部才会显示可生成的脚手架摘要。",
  pluginNameError: "插件名至少要包含一个字母或数字。",
  deviceIdError: "Device ID 必须符合 name.XX，例如 my_driver.01。",
  providersError: "至少提供一个 provider token。",
  modalityError: "Modality 至少要包含一个字母或数字。",
  positiveFloatError: "请输入一个正数。",
  positiveIntError: "请输入一个正整数。",
  channelNamesError: "请至少提供一个 channel 名称。",
  signalChannelNamesCountError: "signal 类型的 channel names 数量必须与 channel count 一致。",
  streamsRequiredError: "至少需要一个 stream。",
  validationBlocked: "当前还不能生成，请先修正草稿中的校验问题。",
  overwriteCancelled: "已取消覆盖。",
  generationSucceeded: "脚手架生成完成。",
  outputExists: "目标目录已经存在。",
  reasonPushDriver: "SDK 会主动把数据推送到你的代码里，因此 Driver 是更自然的默认选择。",
  reasonPushLoop: "虽然数据是 push 型，但你手动保留了 LoopDriver，更适合偏轮询控制风格的设计。",
  reasonPollDriver: "你的代码会自己轮询设备，但如果你想手动掌控生命周期，Driver 依然成立。",
  reasonPollLoop: "你的代码本身是轮询或定时器模型，因此更推荐 LoopDriver。",
  reasonUnsureDriver: "在设备运行模式还不完全明确时，Driver 是更稳妥的起点。",
  reasonUnsureLoop: "虽然运行模式还不明确，但你手动保留了 LoopDriver。",
};

const copyByLanguage: Record<Language, Copy> = { en, zh };

export const sectionOrder: SectionId[] = [
  "identity",
  "connection",
  "driver",
  "streams",
  "dependencies",
];
export const payloadOrder: PayloadType[] = ["signal", "raster", "field", "video"];
export const dataArrivalOrder: DataArrival[] = ["push", "poll", "unsure"];
export const driverKindOrder: DriverKind[] = ["driver", "loop"];

export function getCopy(language: Language): Copy {
  return copyByLanguage[language];
}
