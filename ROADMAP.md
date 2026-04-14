# ModLink Studio 项目路线图

## 背景

当前项目已经完成从 Qt-style driver API 到纯 Python 运行时的主线重构（SDK、Core、Bridge、Server）。基础采集、录制、保存链路已经具备稳定基线，后续路线重点转向实验工作流、回放能力与更高层的数据组织模型。本文档用于定义当前基线，以及后续版本的演进方向。

---

## 一、当前基线

当前仓库以后续设计为前提，先确认以下基线已经成立：

- 安装、搜索设备、连接、实时预览、录制、保存链路已经可用
- 当前 recording 产物已经具备稳定的 `recording.json` / `annotations/` / `streams/` 基础结构，可作为 replay 与数据整理的输入基线
- 单主包 `modlink-studio` 的公开分发策略至少继续沿用到 `0.3.x`
- 后续结构设计优先服务 `recording / session / experiment` 分层，不再把一次录制默认视为实验的一部分
- 历史数据兼容通过薄读取层、导入器或 catalog 适配完成，而不是让旧路径约定持续塑造新主流程

## 二、0.3.0 — 实验工作流与回放

**核心目标：从“能采集”升级为“能组织实验、管理会话、回看录制结果”，同时保留“非实验、即开即录”的轻量工作流。**

**发布策略保持不变：0.3.0 继续沿用单主包 `modlink-studio` 的公开分发方式，不在此版本重新拆分 UI 实现层或官方驱动公开包；插件安装仍优先通过主包 CLI + GitHub 发布物完成。**

### 2.1 数据模型扩展

0.3.0 的主结构不再把“实验”强加给每一次录制。数据模型分成三层：

- `recording`：一次开始到停止之间产生的原子采集资产，可以独立存在、独立回放
- `session`：一次实际执行过程的组织单元，可关联多个 recordings、protocol、操作者、备注等
- `experiment`：更高层的项目/研究/批次组织单元，可关联多个 sessions

这三层关系是：

```text
Experiment（可选）
└── Sessions[]
    └── Recordings[]

Recording（原子资产）
├── metadata
├── annotations
└── streams[]
```

第一版不强制把 `participant` 提升为单独顶层目录；优先将 participant 信息放入 `session.json`，等跨 session 复用需求明确后再拆分。

### 2.1.1 存储结构

0.3.0 的主目录结构调整为：

```text
data/
├─ recordings/
│  └─ rec_<id>/
│     ├─ recording.json
│     ├─ annotations/
│     │  ├─ markers.csv
│     │  └─ segments.csv
│     └─ streams/
│        └─ <stream_id>/
│           ├─ stream.json
│           ├─ chunks.csv
│           └─ chunks/
├─ sessions/
│  └─ ses_<id>/
│     └─ session.json
└─ experiments/
   └─ exp_<id>/
      └─ experiment.json
```

设计原则：

- `recording` 是第一公民，可以不属于任何 session 或 experiment
- `session` 通过 `recording_id` 引用多个 recordings，而不是把 recording 的内部结构绑死到 session 目录语义上
- `experiment` 通过 `session_id` 引用多个 sessions
- 路径键使用稳定的 `experiment_id` / `session_id` / `recording_id`，而不是展示名
- `display_name`、`label`、`notes` 等保持在 metadata 中，不承担路径标识职责

### 2.1.2 多模态 Recording 设计

0.3.0 的 `recording` 需要天然支持多模态数据，因此它本身应被视为“一个多流 bundle”，而不是单流文件夹：

- 一个 recording 可同时包含 signal / raster / field / video 等多条流
- 每条流以 `stream_id` 为唯一目录键，避免 `device/modality` 多级路径在回放和索引时制造额外耦合
- replay 读取只依赖 `recording` 和其中的 `streams/*`，不依赖上层 experiment/session 是否存在
- recording 级 metadata 只描述整次录制；单流的权威描述放在 `streams/<stream_id>/stream.json`

建议的 recording 级 manifest 字段包括：

- `recording_id`
- `status`
- `started_at_ns`
- `stopped_at_ns`
- `session_id`（可空）
- `experiment_id`（可空）
- `protocol_stage_id`（可空）
- `streams[]`（列出 recording 中包含的 stream_id 与路径）

建议的单流 manifest 字段包括：

- `stream_id`
- `payload_type`
- `descriptor`
- `storage_kind`
- `dtype`
- `frame_count`
- `sample_count`
- `chunk_count`

### 2.1.3 落盘格式方向

为了降低 replay 成本并统一多模态读取路径，0.3.0 应继续收敛到“chunked payload + timestamp index”的落盘模型：

- signal / raster / field / video 最终都应能通过统一的 chunk 读取路径恢复为 `FrameEnvelope`
- 回放层不应依赖某一种 payload_type 的特例格式
- 录制格式的首要目标是可回放、可索引、可增量读取，而不是优先追求人工直接编辑

**关键文件改动：**

- `packages/modlink_core/modlink_core/storage/`
  - 作为 shared storage 后端承载 `recording / session / experiment` 的文件持久化
  - 从 `session_{name}` 目录写入模式转为 `recordings/rec_<id>` 原子资产写入模式
  - recording 不再默认绑定 experiment/session 目录层级
  - 写入 recording 级 manifest 和单流 manifest，并为 replay 预留读取接口

- `packages/modlink_core/modlink_core/` 新增 `experiment/` 模块
  - `protocol.py` — 协议定义（阶段列表、每阶段参数、预期时长）
  - `session.py` — 会话数据模型
  - `experiment.py` — 实验数据模型

- `packages/modlink_core/modlink_core/recording/` 新增 replay / catalog 能力
  - 负责列出 recordings / sessions / experiments
  - 负责将 recording 重建为可播放的流数据源
  - 负责在 replay 域内承载导出能力，而不是将导出逻辑分散到采集或 UI 层

当前状态：

- `modlink_core` 内部的 shared storage 第一阶段已完成：顶层 `modlink_core.storage` 已承载 `RecordingStore / SessionStore / ExperimentStore`，recording 写入路径已切到 `recordings/`，writer 已收敛为单一 `StreamRecordingWriter`，并补齐了 recording manifest、annotations、descriptor snapshot、chunk 读回 `FrameEnvelope` 的基础读取接口；外围 bridge / server / UI 还未跟进

**架构原则：**

- 0.3.0 的主结构优先服务新的 experiment/session/replay 语义，而不是被历史路径约定反向塑形
- 历史 recording 的兼容通过薄读取层、导入器或 catalog 适配完成，而不是把旧格式分支散落到新主流程中
- 旧 recording 仍可以被 replay 直接打开，也可以被 session 显式纳入

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

回放放在 0.3.0，是因为它天然属于实验工作流的一部分：录制完成后需要与 marker、segment、session 元数据一起查看和复盘。

- Core 层新增 replay 模块，例如 `packages/modlink_core/modlink_core/recording/replay.py`
- replay 的最小输入单元是 `recording`
- 非实验录制与实验内录制都走同一条 replay 路径
- replay backend 内部分为三层：
  - `RecordingReader`：负责读取 recording、annotations、stream chunk 与时间索引
  - `ReplayPlayer`：负责播放 / 暂停 / 停止 / 倍速等实时回放控制
  - `ExportService`：负责非实时导出 job，和 player 共用 reader，但不走实时播放链路
- 回放对外尽量复用实时流的 `StreamDescriptor + FrameEnvelope + StreamBus` 入口，降低 UI 重写成本
- 第一版能力只做：
  - 打开 recording
  - 播放 / 暂停 / 停止 / 从头播放
  - 1x / 2x / 4x 倍速
  - marker / segment 联动展示
  - 发起导出任务并查看导出状态
- 第一版明确不做：
  - 时间轴任意拖拽
  - 多 recording 拼接
  - live / replay 混播

### 2.3.1 导出能力

导出属于 replay backend 的一部分，因为它和回放共用同一套 recording 读取能力；但导出不是 player 的职责。

设计原则：

- 采集落盘格式优先服务稳定写入、统一回放与可增量读取
- 导出格式优先服务分析、共享、可视化与对外交换
- 导出通过后台 job 运行，不要求实时
- 导出产物默认写入独立的 `exports/` 目录，而不是回写原始 recording 目录
- 导出格式扩展通过内建 exporter 注册表完成，不预先引入插件式复杂抽象

第一版导出分成两类：

- Analysis export
  - `signal_csv`
  - `signal_npz`
  - `raster_npz`
  - `field_npz`
  - `video_frames_zip`
- Presentation export
  - `video_mp4`
  - `raster_mp4`
  - `field_mp4`
  - `recording_bundle_zip`

后续可继续扩展：

- BIDS
- NWB
- 更完整的批量 session / experiment 导出

### 2.4 UI 变更

- 实验管理页面（新建实验 → 填写受试者 → 选择协议 → 进入 session）
- Session 内的录制面板升级：显示当前阶段、进度、下一步指引
- Replay 页面或 replay 模式：打开 recording 后复用现有预览组件进行复盘
- Replay 页面内增加导出区域或导出侧栏，支持选择格式、配置参数、查看导出任务进度
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

**AI 层不侵入 Core 运行时。** 它是 Core 之上的一个独立服务，通过已有的 API（DriverPortal、RecordingBackend、SettingsService）操作，和用户手动操作走同一条路径。

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
│  Recording, Settings      │
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
当前基线
  ├── 基础采集链路稳定可用
  ├── 当前 recording 格式可作为 replay 输入基线
  ├── 单主包公开分发策略延续
  └── 重点转向 experiment / session / replay
      │
      ▼
0.3.x  实验工作流与回放
  ├── Recording / Session / Experiment 分层模型
  ├── Protocol 定义和存储
  ├── 录制回放
  ├── Replay backend 内建导出能力
  ├── UI：实验管理页面
  ├── recording 原子资产化
  ├── 多模态 recording 格式标准化
  └── 保持单主包公开分发
      │
      ▼
0.4.x  AI 辅助
  ├── AI Assistant Service
  ├── LLM 集成（Claude API）
  ├── 协议自动编排
  ├── AI 助手 UI 面板
  ├── 上下文感知的建议系统
  └── 将 `modlink-plugin` 扩展为更完整的插件管理工具
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

1. **敲定多层数据模型（进行中）** — 落定 `recording / session / experiment` 的边界、ID 规则与引用关系
2. **完成 recording schema 设计（进行中）** — `modlink_core` 内部第一版 `recording.json`、单流 `stream.json`、annotations 与 chunk 索引已经落地，后续还需要结合 catalog / replay 再收 schema
3. **实现 recording catalog（进行中）** — shared storage 已具备基础 `list/read` 能力，后续继续收口成统一的 recordings / sessions / experiments 查询入口
4. **实现 replay 核心链路（待开始）** — 基于 recording 重建 `StreamDescriptor + FrameEnvelope + StreamBus`，先完成播放 / 暂停 / 停止 / 倍速
5. **设计并实现 export service（待开始）** — 在 replay backend 中支持导出 job、格式选择、进度与结果路径
6. **推进多模态落盘格式统一（进行中）** — `modlink_core` 内部已收敛到单一 `StreamRecordingWriter` + 统一的 chunked payload + timestamp index 主格式，后续继续围绕 replay/export 校正 reader 侧契约
7. **补齐 session / protocol 工作流（待开始）** — 支持会话创建、recording 归档、阶段信息与操作者备注
8. **保留历史数据导入路径（待开始）** — 通过薄读取层或导入器兼容旧 recording，而不是让旧结构继续塑造新主流程

---

## 六、技术债务（可穿插在任意版本中处理）

- QML 迁移决策：是继续并行还是确定方向
- mypy/pyright 类型检查（从 SDK 开始）
- UI 测试覆盖提升
- 旧插件清理
