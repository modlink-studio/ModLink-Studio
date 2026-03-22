# ModLink Studio

面向多设备接入、多模态采集与展示的数据平台。

这个仓库从 `openbciganglionui` 迁移而来，但目标已经不再是单一设备的专用工具，而是一个能够承载多种设备、多种数据流和多种采集界面的 `monorepo`。设备开发者可以通过实现自己的 driver plugin，把各自设备接入这套平台，用统一的方式完成展示、预览、标注和采集。

![OpenBCI Ganglion UI screenshot](assets/ui-demo.png)

## 项目定位

`ModLink Studio` 的目标不是做一个只服务某一块板卡的 demo，而是做一套可复用的采集基础设施。

这套基础设施希望解决的问题包括：

- 不同设备用不同驱动接入，但上层展示和采集流程尽量统一
- 不同模态的数据都能用一致的数据结构在系统内流转
- 设备开发者只需要关注自己的驱动实现，不需要重复搭一整套 UI 和录制流程
- 采集任务可以共享统一的设置、总线、标注和录制逻辑

## 迁移背景

这个仓库的起点是 `openbciganglionui`。

原项目已经实现了面向 `OpenBCI Ganglion` 的连接、预览、标注和录制流程，说明整条采集链路是可行的。现在我们把它作为迁移起点，把其中有价值的运行时模型、采集逻辑和 UI 经验逐步抽到新的 `ModLink Studio` 结构里。

因此当前仓库里会同时看到两条线：

- `deprecated/src/openbciganglionui/`
  现有的旧应用实现，也是当前最完整、最可运行的参考
- `packages/`
  正在建设中的新 monorepo 基础层，后续新的通用能力主要会沉淀在这里

## 面向谁

这个项目主要面向两类角色：

- 平台维护者：维护共享数据模型、总线、录制、设置、公共 UI 和应用组装逻辑
- 设备接入者：为自己的设备实现 plugin/driver，把设备数据接到平台里

理想情况下，设备接入者只需要完成“设备如何连接、如何发流、每个流长什么样”这部分，平台本身负责把这些流交给显示、标注和录制模块。

## 当前 monorepo 结构

```text
modlink-studio/
├─ apps/
│  └─ modlink_studio/
├─ packages/
│  ├─ modlink_sdk/
│  ├─ modlink_core/
│  └─ modlink_ui/
├─ plugins/
├─ vpdocs/
└─ deprecated/
```

当前各目录的职责可以理解为：

- `apps/`
  面向具体场景的应用组装层，未来不同设备组合或实验场景可以在这里落应用入口
- `packages/modlink_sdk/`
  面向 driver/plugin 开发者的最小 SDK，提供共享数据模型和 driver 契约
- `packages/modlink_core/`
  平台核心能力，例如流总线、录制任务、设置服务、driver portal 和运行时组装
- `packages/modlink_ui/`
  未来可复用的 UI 组件和 UI 基础设施
- `plugins/`
  具体设备插件所在的位置，后续官方维护和实验性 driver 都放这里
- `deprecated/src/openbciganglionui/`
  迁移参考来源，保留现有 Ganglion 专用实现，供抽取和对照

## 驱动接入思路

后续接入设备时，推荐遵循下面这条思路：

1. 基于 `modlink_sdk` 实现自己的 driver/plugin
2. 为设备定义它会产生哪些 stream，以及每个 stream 的 `StreamDescriptor`
3. 驱动通过 signal 持续发出 `FrameEnvelope`
4. `modlink_core` 的总线、录制和其他上层模块消费这些流
5. UI 或具体 app 再根据这些统一流去做展示和采集交互

也就是说，平台希望把“设备怎么接”和“数据怎么被展示/录制”拆开。

## 当前状态

目前仓库已经以 `ModLink Studio` 为默认入口，核心方向也已经切到新的分层结构：

- `apps/` 负责应用入口和最终组装
- `packages/` 负责 SDK、Core 和 UI 基础层
- `plugins/` 负责按需挂载的设备 driver
- `deprecated/src/openbciganglionui/` 保留为迁移参考

也就是说，这个仓库的重点已经不是继续扩大单设备专用应用，而是稳定一套可复用的设备接入和采集平台。

## 开发目标

接下来这个仓库的重点不是继续把 `Ganglion UI` 做成更大的单设备应用，而是逐步完成下面这些事情：

- 稳定共享数据模型和核心运行时边界
- 明确 driver 接入方式，让不同设备都能复用平台能力
- 把现有 `openbciganglionui` 中通用的部分抽到 `packages/`
- 为未来的多模态展示和采集界面预留统一的应用组织方式

## 当前开发方式

当前本地开发优先使用新的 `modlink-studio` 入口：

```bash
uv sync
uv run modlink-studio
```

或者：

```bash
uv run python -m modlink_studio
```

如果你还在排查旧入口，也可以继续用 `openbciganglionui` 兼容命令，但新项目身份和默认入口已经切到 `ModLink Studio`。

如果你需要某个可选 driver plugin，推荐在启动时临时附加它。例如启用
`openbciganglion`：

```bash
uv sync
uv run --with ./plugins/openbciganglion modlink-studio
```

如果你正在开发某个 plugin，希望本地代码修改立即生效，推荐使用 editable
模式启动：

```bash
uv sync
uv run --with-editable ./plugins/openbciganglion modlink-studio
```

默认的 `uv sync` 不会安装这些插件，只有显式通过 `--with` /
`--with-editable` 附加时才会参与本次运行。

## 文档

项目文档目前使用 `VitePress` 维护，源码位于 `vpdocs/`。

文档源码和 GitHub Pages 发布仓库现在分开维护：

- 当前代码仓负责保存文档源码
- `modlink-studio.github.io` 仓库负责承载最终静态站点

本地预览：

```bash
npm ci
npm run docs:vp:dev
```

本地构建：

```bash
npm ci
npm run docs:pdoc:build
npm run docs:vp:build
```

推荐发布方式是自动发布：当前代码仓已经提供了
`.github/workflows/publish-docs.yml`，会在 `main` 分支更新后自动构建文档并同步到
`modlink-studio.github.io`。

要启用这条自动发布链，需要先在 `ModLink-Studio` 仓库里配置一个 GitHub Actions secret：

- `DOCS_DEPLOY_TOKEN`
  建议使用 fine-grained personal access token，并只授予 `modlink-studio/modlink-studio.github.io` 这个仓库的 `Contents: Read and write` 权限

本地兜底方式仍然保留。如果你本地已经把 `modlink-studio.github.io` 仓库克隆到当前仓库旁边，可以直接用：

```bash
powershell -ExecutionPolicy Bypass -File .\scripts\export-docs.ps1
```

这个脚本会构建文档，并把 `vpdocs/.vitepress/dist/` 的内容同步到
`..\modlink-studio.github.io\`。

## 给设备开发者的说明

如果你后续要把自己的设备接进来，建议先关注三件事：

- 设备有哪些稳定的数据流需要暴露
- 每个流的 payload 应该如何描述
- 驱动层和上层采集/展示层之间应该通过什么最小接口解耦

你不需要从零写一整套采集软件；这个仓库要做的，正是把那些重复工作沉淀成共享平台能力。

## 说明

这个 README 现在描述的是项目目标和当前迁移方向，而不是最终完成态。随着 `packages/`、`apps/` 和新的应用入口逐步成形，这份文档也会继续更新。



