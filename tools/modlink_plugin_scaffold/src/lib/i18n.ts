import type {DataArrival, DriverKind, Language, PayloadType, PreviewTab, SectionId} from "./types.js";

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
  previewTabs: Record<PreviewTab, string>;
  sections: Record<SectionId, string>;
  payloadOptions: Record<PayloadType, string>;
  dataArrivalOptions: Record<DataArrival, string>;
  driverKindOptions: Record<DriverKind, string>;
  invalidPreviewPlaceholder: string;
  validationErrorsHeader: string;
  defaultStreamName: string;
  generatedFilesLabel: string;
  commandsLabel: string;
  summaryTitle: string;
  statusPrefix: string;
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
  helpLine: "Tab: next section | Up/Down: rows | Left/Right: choices | Enter: edit or run | [: prev preview | ]: next preview | g: generate | q: quit",
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
  previewTabs: {
    summary: "Summary",
    driver: "driver.py",
    pyproject: "pyproject.toml",
    readme: "README.md"
  },
  sections: {
    identity: "Identity",
    connection: "Connection",
    driver: "Driver Type",
    streams: "Streams",
    dependencies: "Dependencies"
  },
  payloadOptions: {
    signal: "signal",
    raster: "raster",
    field: "field",
    video: "video"
  },
  dataArrivalOptions: {
    push: "SDK pushes data into your code",
    poll: "Your code polls on its own loop",
    unsure: "You are still not sure"
  },
  driverKindOptions: {
    driver: "Driver",
    loop: "LoopDriver"
  },
  invalidPreviewPlaceholder: "Preview is unavailable until the draft passes validation.",
  validationErrorsHeader: "Validation errors",
  defaultStreamName: "Stream",
  generatedFilesLabel: "Generated files",
  commandsLabel: "Next commands",
  summaryTitle: "Scaffold summary",
  statusPrefix: "Status",
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
  reasonPushLoop: "The SDK pushes data, but LoopDriver was kept manually for a polling-style design.",
  reasonPollDriver: "Your code polls on its own schedule, but Driver is still valid if you want to own the lifecycle.",
  reasonPollLoop: "Your code polls on its own loop or timer, so LoopDriver is the recommended base class.",
  reasonUnsureDriver: "Driver is the safer starting point until the device runtime pattern is clear.",
  reasonUnsureLoop: "LoopDriver was kept manually even though the runtime pattern is still uncertain."
};

const zh: Copy = {
  appTitle: "ModLink 插件脚手架",
  appSubtitle: "基于 React + Ink 的 Python driver 开发工具",
  helpLine: "Tab: 下一分区 | 上下: 行切换 | 左右: 切换选项 | Enter: 编辑或执行 | [: 上一个预览 | ]: 下一个预览 | g: 生成 | q: 退出",
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
  previewTabs: {
    summary: "摘要",
    driver: "driver.py",
    pyproject: "pyproject.toml",
    readme: "README.md"
  },
  sections: {
    identity: "基本信息",
    connection: "连接方式",
    driver: "Driver 类型",
    streams: "Streams",
    dependencies: "依赖"
  },
  payloadOptions: {
    signal: "signal",
    raster: "raster",
    field: "field",
    video: "video"
  },
  dataArrivalOptions: {
    push: "SDK 主动把数据推到你的代码里",
    poll: "你的代码自己轮询设备",
    unsure: "现在还不确定"
  },
  driverKindOptions: {
    driver: "Driver",
    loop: "LoopDriver"
  },
  invalidPreviewPlaceholder: "当前草稿还未通过校验，因此暂时无法预览生成文件。",
  validationErrorsHeader: "校验问题",
  defaultStreamName: "Stream",
  generatedFilesLabel: "生成的文件",
  commandsLabel: "后续命令",
  summaryTitle: "脚手架摘要",
  statusPrefix: "状态",
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
  reasonUnsureLoop: "虽然运行模式还不明确，但你手动保留了 LoopDriver。"
};

const copyByLanguage: Record<Language, Copy> = {en, zh};

export const sectionOrder: SectionId[] = ["identity", "connection", "driver", "streams", "dependencies"];
export const previewOrder: PreviewTab[] = ["summary", "driver", "pyproject", "readme"];
export const payloadOrder: PayloadType[] = ["signal", "raster", "field", "video"];
export const dataArrivalOrder: DataArrival[] = ["push", "poll", "unsure"];
export const driverKindOrder: DriverKind[] = ["driver", "loop"];

export function getCopy(language: Language): Copy {
  return copyByLanguage[language];
}
