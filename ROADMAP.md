# ModLink Studio 项目路线图

## 背景

当前项目处于 0.2.0 开发阶段，核心目标是从 0.1.x 的 Qt-style driver API 切换到纯 Python 运行时。技术重构已基本完成（SDK、Core、Bridge、Server），但距离「稳定可发布、可持续扩展」的产品状态仍有明确缺口。本文档用于定义从当前状态到 0.2.0 发布、再到后续实验工作流与 AI 辅助能力的版本路线。

---

## 一、0.2.0 发布目标：基础采集链路稳定可用

**0.2.0 的发布目标是：安装、搜索设备、连接、采集、录制、保存这条基础链路稳定可用，关键流程不中断。**

### 1.1 基础链路完整性检查

以下是目前已就位和需要补齐的项目：

| 链路环节 | 状态 | 需要做的事 |
|---|---|---|
| 安装与启动 | 基本就位 | 完成 TestPyPI rehearsal，并确认 PyPI 目标安装命令可在干净环境中工作；`modlink-studio` 命令可用 |
| 设备搜索 | 已就位 | Driver.search() → SearchResult → UI 展示 |
| 设备连接 | 已就位 | 选择 SearchResult → Driver.connect_device() → 流描述发现 |
| 流预览 | 已就位 | SignalStreamView / RasterView / VideoView |
| 开始/停止采集 | 已就位 | AcquisitionBackend + UI 面板 |
| 录制保存 | 已就位 | StorageManager → 文件系统 |
| 录制回放 | 延后到 0.3.0 | 0.2.0 先保证录制格式稳定、元数据完整、保存结果可见 |
| 插件安装 | 基本就位 | extras + entry point 发现 |

### 1.2 0.2.0 发布门槛

**P0 — 发布阻塞项：**

- [x] **基础 UI 体验修复（已完成）**
  - [x] 修复 `test_signal_preview.py` 中 SignalStreamView 构造签名不匹配的 pre-existing 问题
  - [x] 确保 modlink_server 能在 dev 环境下跑测试（fastapi 依赖）
  - [x] 首次启动引导：默认 widgets 主页面在没有可预览流时提供明确提示，而不是空白界面

- [x] **录制链路稳定化（已完成）**
  - [x] 录制完成后，UI 明确展示保存路径、session 名称、recording_id 等结果信息
  - [x] `recording.json` / `markers.csv` / `segments.csv` / `streams/` 目录结构固定下来，作为 0.3.0 回放的输入基础
  - [x] 录制失败时，错误原因和失败 recording 路径能被用户看到，而不是静默失败

- [ ] **文档与发布准备（进行中）**
  - [x] README 更新 0.2.0 安装说明与工作区开发说明
  - [x] 0.2.0 CHANGELOG
  - [x] 文档站 breaking change 说明同步
  - [ ] TestPyPI rehearsal
  - [ ] PyPI 发布前干净环境安装验证

- [x] **运行时稳健性收口（已完成）**
  - [x] Settings 文件损坏时不再静默丢设置，损坏内容会备份并记录 warning
  - [x] `modlink_server` `/events` 增加 SSE keepalive comment，空闲连接不再长期静默
  - [x] `modlink_core` / `modlink_server` / 官方插件关键异常路径补齐最小 logging
  - [x] Qt Widgets preview 完成最小主题适配，预览不再固定白底与固定次级文本颜色

**P1 — 建议在 0.2.x 尽快完成：**

- [ ] **设置面板完善**
  - 录制输出目录选择（当前 UI 有但后端集成需确认完整）
  - 默认采样率、缓冲区大小等全局设置

- [ ] **录制元数据增强**
  - recording.json 增加 `notes`（自由文本备注）字段
  - recording.json 增加 `operator`（操作者标识）字段
  - 这些字段在 0.3.0 的实验工作流中会成为必需品，0.2.0 先埋好结构

### 1.3 0.2.0 范围外

- 录制回放（整体延后到 0.3.0）
- 实验协议（protocol）系统
- 受试者管理
- AI 辅助功能
- Web 前端
- QML UI 替代 Qt Widgets（保持两条线并行，不做切换）

### 1.4 0.2.0 可用性标准

```
0.2.0 应达到以下可用性标准：
1. pip install modlink-studio + 安装一个官方插件
2. 启动应用，搜索并连接设备
3. 看到实时流预览
4. 开始录制，添加 marker，停止录制
5. 明确看到录制结果保存到了哪里，录制文件结构清晰、元数据完整
```

---

## 二、0.3.0 — 实验工作流与回放

**核心目标：从“能采集”升级为“能组织实验、管理会话、回看录制结果”。**

### 2.1 数据模型扩展

当前 `recording.json` 只足够表达单次录制，需要进一步引入实验与会话层级：

```
Experiment（实验）
├── Participant（受试者）
│   ├── participant_id
│   ├── demographics (年龄、性别、利手等，可扩展)
│   └── custom_fields
├── Session 1（一次实验会话）
│   ├── session_id
│   ├── protocol 引用
│   ├── recordings[] (多次录制)
│   └── notes
├── Session 2
└── ...
```

**关键文件改动：**

- `packages/modlink_core/modlink_core/acquisition/storage/manager.py`
  - 扩展存储目录结构，支持 experiment/participant/session 层级
  - 向后兼容 0.2.0 的扁平 session_{name} 格式
  - 保持 0.2.0 的 recording 目录作为最小可复用单元；0.3.0 是在其外层增加 experiment/session 包装，而不是推翻旧 recording

- `packages/modlink_core/modlink_core/` 新增 `experiment/` 模块
  - `protocol.py` — 协议定义（阶段列表、每阶段参数、预期时长）
  - `participant.py` — 受试者数据模型
  - `session.py` — 会话数据模型（关联 experiment + participant）

**兼容原则：**

- 0.2.0 录出来的单个 recording 目录仍然有效，不因为 0.3.0 的 experiment/session 引入而失效
- 0.3.0 的 session 只是把多个 recordings、notes、participant 信息组织起来
- 旧 recording 可以被直接纳入 session，也可以作为 replay 的直接输入

### 2.2 协议（Protocol）系统

协议定义一个实验的结构：

```python
@dataclass
class ProtocolStage:
    name: str                          # "resting_state", "p300_stimulus", ...
    duration_seconds: float | None     # None = 手动控制
    default_recording_label: str       # 预填的录制标签
    required_streams: list[str]        # 需要哪些设备流
    default_settings: dict             # 此阶段的默认参数
    instructions: str                  # 给操作者的文字指引

@dataclass
class Protocol:
    name: str                          # "P300_Oddball", "SSVEP_Check", ...
    description: str
    stages: list[ProtocolStage]
    metadata: dict
```

### 2.3 回放与复盘

回放放在 0.3.0，而不是 0.2.0，原因是它天然属于实验工作流的一部分：录制完成后需要与 marker、segment、session 元数据一起查看和复盘。

- Core 层新增 replay 模块，例如 `packages/modlink_core/modlink_core/acquisition/replay.py`
- 输入直接使用 0.2.0 已稳定下来的 recording 目录格式
- 回放对外尽量复用实时流的 `StreamDescriptor + FrameEnvelope + StreamBus` 入口，降低 UI 重写成本
- 第一版能力只做：
  - 打开 recording
  - 播放 / 暂停 / 停止 / 从头播放
  - 1x / 2x / 4x 倍速
  - marker / segment 联动展示
- 第一版明确不做：
  - 时间轴任意拖拽
  - 多 recording 拼接
  - live / replay 混播

### 2.4 UI 变更

- 实验管理页面（新建实验 → 填写受试者 → 选择协议 → 进入 session）
- Session 内的录制面板升级：显示当前阶段、进度、下一步指引
- Replay 页面或 replay 模式：打开 recording 后复用现有预览组件进行复盘
- 受试者信息表单

---

## 三、0.4.0 — AI 辅助 Session 管理

**核心目标：AI 不控制硬件，只承担编排、建议、预填写等辅助职责；开始、停止、下一步等关键控制权始终由用户保留。**

### 3.1 AI 的角色定义

```
用户视角的实验流程：

  ┌─────────────────────────────────────────────────┐
  │  AI 助手面板（侧边栏/对话式）                      │
  │                                                   │
  │  AI: 这是一个 P300 Oddball 实验。我帮你填好了       │
  │      协议参数。下一步请连接 OpenBCI 设备。          │
  │                                                   │
  │  AI: 设备已连接，信号质量良好。                     │
  │      第一阶段是"静息态"，持续 3 分钟。              │
  │      我已经帮你填好了 recording_label = "rest_1"，  │
  │      点击"开始采集"即可。                          │
  │                                                   │
  │  [用户点击开始] → 3分钟后点击停止                    │
  │                                                   │
  │  AI: "rest_1" 录制完成。                           │
  │      下一阶段是"刺激态"，参数已填好。               │
  │      点击"开始采集"继续。                          │
  │                                                   │
  │  [用户点击开始] → 用户点击停止                      │
  │  ...                                              │
  │                                                   │
  │  AI: 实验全部完成。共 6 段录制，总时长 25 分钟。    │
  │      录制文件已保存到 experiments/p300_001/        │
  └─────────────────────────────────────────────────┘
```

### 3.2 架构设计

**AI 层不侵入 Core 运行时。** 它是 Core 之上的一个独立服务，通过已有的 API（DriverPortal、AcquisitionBackend、SettingsService）操作，和用户手动操作走同一条路径。

```
┌──────────────────────────┐
│  AI Assistant Service     │  ← 新模块
│  (LLM + 状态机)          │
├──────────────────────────┤
│  Experiment Manager       │  ← 0.3.0 新增
│  (Protocol, Session,      │
│   Participant)           │
├──────────────────────────┤
│  ModLink Core (现有)      │
│  Engine, DriverPortal,    │
│  Acquisition, Settings    │
└──────────────────────────┘
```

**新增模块：** `packages/modlink_ai/`（或作为独立包）

```
packages/modlink_ai/
├── modlink_ai/
│   ├── __init__.py
│   ├── assistant.py        # AI 助手主类
│   ├── protocol_llm.py     # LLM 与协议系统的交互
│   ├── context.py          # 当前实验上下文（设备状态、录制进度等）
│   └── prompts/            # 提示词模板
│       ├── experiment.py
│       └── session.py
└── pyproject.toml
```

### 3.3 AI 调用链路

```
用户选择/描述实验 → LLM 理解意图
  → LLM 返回 Protocol 结构（阶段列表 + 参数）
  → 用户确认或修改
  → AI 按阶段推进：
      1. 填写当前阶段的 session 参数（recording_label、marker 预设等）
      2. 建议用户检查设备状态
      3. 等待用户操作（开始/停止）
      4. 读取录制结果，更新进度
      5. 填写下一阶段参数
      6. 重复直到实验完成
```

### 3.4 LLM 集成方案

- 使用 Claude API（anthropic SDK）
- 用户在设置中配置 API key
- 预留 provider 抽象层，后续可接 OpenAI 等其他 LLM
- 每次调用传入当前实验上下文（设备列表、流描述、已完成阶段、当前参数），LLM 返回结构化 JSON
- UI 侧以对话面板呈现 AI 的建议，同时直接修改表单字段

### 3.5 UI 集成

- 在主窗口右侧或底部增加 AI 助手面板（类似聊天窗口）
- AI 的建议同时以两种形式呈现：
  1. 对话消息（"我已经帮你填好了参数"）
  2. 直接修改 UI 表单（recording_label 输入框高亮表示被 AI 填写）
- 用户随时可以覆盖 AI 填写的任何字段
- 关键操作（开始录制、停止录制）必须由用户手动触发

---

## 四、版本时间线

```
0.2.x  基础采集链路稳定可用（当前）
  ├── UI 体验修复
  ├── 元数据增强（notes, operator）
  ├── 录制链路稳定化（保存结果清晰可见）
  └── 文档 + 发布准备
      │
      ▼
0.3.x  实验工作流与回放
  ├── Experiment / Participant / Session 数据模型
  ├── Protocol 定义和存储
  ├── 录制回放
  ├── UI：实验管理页面
  ├── 存储结构升级（向后兼容）
  └── 录制文件格式标准化
      │
      ▼
0.4.x  AI 辅助
  ├── AI Assistant Service
  ├── LLM 集成（Claude API）
  ├── 协议自动编排
  ├── AI 助手 UI 面板
  └── 上下文感知的建议系统
      │
      ▼
0.5.x  生态扩展
  ├── 插件注册中心
  ├── 数据导出工具（HDF5/BIDS）
  ├── 回放 API 服务化 / Web 化
  └── Web UI（基于已有 Server API）
```

---

## 五、当前优先级（按顺序）

1. **锁定 0.2.0 发布范围（已完成）** — 明确 0.2.0 只承诺稳定采集、录制、保存，不再将回放继续纳入当前版本
2. **首次启动体验（已完成）** — 默认页面在没有可预览流时给出清晰引导，而不是空白页
3. **录制链路稳定化（已完成）** — UI 上明确显示保存路径、recording_id 与失败原因
4. **运行时稳健性收口（已完成）** — settings 损坏备份、SSE keepalive、最小 logging 与 widgets preview 主题适配已完成
5. **元数据字段预留（待开始）** — 在 recording.json 结构中提前埋好 notes、operator 等字段
6. **文档与发布验证（进行中）** — 安装说明、CHANGELOG、文档站 breaking change 已更新；TestPyPI rehearsal 与 PyPI 发布前验证待执行
7. **清理仓库（已完成）** — `deprecated/` 已移除；旧插件清理不再作为 0.2.0 阻塞项

---

## 六、技术债务（可穿插在任意版本中处理）

- QML 迁移决策：是继续并行还是确定方向
- mypy/pyright 类型检查（从 SDK 开始）
- UI 测试覆盖提升
- 旧插件清理
