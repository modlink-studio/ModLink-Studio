# ModLink Studio

面向组内使用的多模态数据采集项目。

这个仓库从 `openbciganglionui` 迁移而来，但目标已经不再是单一设备的专用工具，而是一个能够承载多种设备、多种数据流和多种采集界面的 `monorepo`。后续组内师兄师姐可以通过自己实现 `modlink_driver`，把各自设备接入这套平台，用统一的方式完成展示、预览、标注和采集。

![OpenBCI Ganglion UI screenshot](docs/images/ui-demo.png)

## 项目定位

`ModLink Studio` 的目标不是做一个只服务某一块板卡的 demo，而是做一套组内可复用的采集基础设施。

这套基础设施希望解决的问题包括：

- 不同设备用不同驱动接入，但上层展示和采集流程尽量统一
- 不同模态的数据都能用一致的数据结构在系统内流转
- 设备开发者只需要关注自己的驱动实现，不需要重复搭一整套 UI 和录制流程
- 采集任务可以共享统一的设置、总线、标注和录制逻辑

## 迁移背景

这个仓库的起点是 `openbciganglionui`。

原项目已经实现了面向 `OpenBCI Ganglion` 的连接、预览、标注和录制流程，说明整条采集链路是可行的。现在我们把它作为迁移起点，把其中有价值的运行时模型、采集逻辑和 UI 经验逐步抽到新的 `ModLink Studio` 结构里。

因此当前仓库里会同时看到两条线：

- `src/openbciganglionui/`
  现有的旧应用实现，也是当前最完整、最可运行的参考
- `packages/`
  正在建设中的新 monorepo 基础层，后续新的通用能力主要会沉淀在这里

## 面向谁

这个项目主要服务组内同学，尤其是两类角色：

- 平台维护者：维护共享数据模型、总线、录制、设置、公共 UI 和应用组装逻辑
- 设备接入者：为自己的设备实现 `modlink_driver`，把设备数据接到平台里

理想情况下，设备接入者只需要完成“设备如何连接、如何发流、每个流长什么样”这部分，平台本身负责把这些流交给显示、标注和录制模块。

## 当前 monorepo 结构

```text
modlink-studio/
├─ apps/
├─ packages/
│  ├─ modlink_shared/
│  ├─ modlink_core/
│  ├─ modlink_drivers/
│  └─ modlink_ui/
├─ tests/
├─ docs/
└─ scripts/
```

当前各目录的职责可以理解为：

- `apps/`
  面向具体场景的应用组装层，未来不同设备组合或实验场景可以在这里落应用入口
- `packages/modlink_shared/`
  共享运行时模型，例如帧结构、流描述、信号协议等
- `packages/modlink_core/`
  平台核心能力，例如流总线、录制任务、设置服务、运行时组装
- `packages/modlink_drivers/`
  驱动基类和后续具体驱动实现所在的位置
- `packages/modlink_ui/`
  未来可复用的 UI 组件和 UI 基础设施
- `src/openbciganglionui/`
  迁移参考来源，保留现有 Ganglion 专用实现，供抽取和对照

## 驱动接入思路

后续组内同学接入设备时，推荐遵循下面这条思路：

1. 在 `modlink_drivers` 体系下实现自己的驱动类
2. 为设备定义它会产生哪些 stream，以及每个 stream 的 `StreamDescriptor`
3. 驱动通过 signal 持续发出 `FrameEnvelope`
4. `modlink_core` 的总线、录制和其他上层模块消费这些流
5. UI 或具体 app 再根据这些统一流去做展示和采集交互

也就是说，平台希望把“设备怎么接”和“数据怎么被展示/录制”拆开。

## 当前状态

目前仓库处在迁移期，整体状态是：

- `openbciganglionui` 仍然是当前最完整的可运行实现
- `packages/` 里的基础层正在补齐，用来承接新的通用架构
- 项目级入口、命名和发布配置还没有完全切换到 `ModLink Studio`
- 一些文档和目录已经是新的方向，但仍会保留旧项目痕迹

这意味着：现在这个仓库既是正在运行的旧项目，也是正在建设的新平台。

## 开发目标

接下来这个仓库的重点不是继续把 `Ganglion UI` 做成更大的单设备应用，而是逐步完成下面这些事情：

- 稳定共享数据模型和核心运行时边界
- 明确 driver 接入方式，让不同设备都能复用平台能力
- 把现有 `openbciganglionui` 中通用的部分抽到 `packages/`
- 为未来的多模态展示和采集界面预留统一的应用组织方式

## 当前开发方式

当前依赖和运行方式还沿用旧项目配置，因此本地开发仍然可以先这样启动：

```bash
uv sync
uv run openbciganglionui
```

或者：

```bash
uv run python -m openbciganglionui
```

这里启动的是迁移前的 Ganglion 应用，不是最终形态的 `ModLink Studio` 通用入口。

## 给组内设备开发者的说明

如果你后续要把自己的设备接进来，建议先关注三件事：

- 设备有哪些稳定的数据流需要暴露
- 每个流的 payload 应该如何描述
- 驱动层和上层采集/展示层之间应该通过什么最小接口解耦

你不需要从零写一整套采集软件；这个仓库要做的，正是把那些重复工作沉淀成共享平台能力。

## 说明

这个 README 现在描述的是项目目标和当前迁移方向，而不是最终完成态。随着 `packages/`、`apps/` 和新的应用入口逐步成形，这份文档也会继续更新。
