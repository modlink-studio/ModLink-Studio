# 安装与发布

本页汇总 `0.2.0` 的安装目标、官方插件安装方式和源码运行方式。

## 0.2.0 发布状态

`0.2.0` 目前仍未正式发布。当前文档描述的是 `0.2.0` 的目标发布状态：

- `0.2.0` 是一次明确的 breaking change
- 正式公开发布渠道将切到 **PyPI**
- 发布前会先完成一次 **TestPyPI rehearsal**
- `TestPyPI` 只用于发布链路演练，不作为日常安装源

## 0.2.0 升级说明

`0.2.0` 的主线代码和文档都以纯 Python runtime 为准：

- `modlink_sdk` / `modlink_core` 已不再依赖 Qt 运行时
- 外部 driver 不再以 `sig_frame` / `sig_connection_lost` 作为正式宿主契约
- `LoopDriver` 不再基于 `QTimer`
- 如果你手头还有 `0.1.x` 的 Qt-style driver，需要按新的 SDK 契约迁移

当前 UI 仍在适配期，但 backend 已经完成去 Qt 化；`0.2.0` 的发布边界是稳定采集、录制和保存，不包含回放。

## 正式安装命令

`0.2.0` 正式发布后的主安装入口将是：

```bash
python -m pip install modlink-studio
```

安装完成后，正式入口是：

```bash
modlink-studio
```

调试入口保留为：

```bash
python -m modlink_studio
```

## 安装官方插件

官方插件继续按需通过 extras 安装，不会随主应用一次性全部启用。

可用 extras：

- `official-host-camera`
- `official-host-microphone`
- `official-openbci-ganglion`

安装示例：

```bash
python -m pip install "modlink-studio[official-host-camera]"
```

```bash
python -m pip install "modlink-studio[official-host-camera,official-host-microphone]"
```

```bash
python -m pip install "modlink-studio[official-openbci-ganglion]"
```

当前保留支持的官方插件包名是：

- `modlink-plugin-host-camera`
- `modlink-plugin-host-microphone`
- `modlink-plugin-openbci-ganglion`

## 从源码运行

如果目标是开发、联调或跟进仓库当前实现，可以直接从源码运行，而不是等待正式发布包。

前置要求：

- Python 3.13
- Git
- `uv`

获取源码并同步环境：

```bash
git clone https://github.com/modlink-studio/ModLink-Studio.git
cd ModLink-Studio
uv sync
```

从仓库直接启动主宿主：

```bash
uv run modlink-studio
```

按需附加官方插件：

```bash
uv run --extra official-host-camera modlink-studio
```

```bash
uv run --extra official-host-camera --extra official-host-microphone modlink-studio
```

如果要直接联调 QML 宿主：

```bash
uv run modlink-studio-qml
```

## 独立脚手架工具

driver 脚手架现在作为独立 npm 工具提供，而不是 `modlink-studio` 的运行时依赖：

```bash
npx @modlink-studio/plugin-scaffold --zh
```

仓库内联调脚手架：

```bash
npm install
npm --workspace @modlink-studio/plugin-scaffold run dev -- --zh
```

更完整的 driver 开发说明见 [SDK 开发者指南](/sdk)。

## 发布前验证

在 `0.2.0` 正式发布前，需要先完成一次 **TestPyPI rehearsal**。这一步只用于验证发布链路和安装命令，不作为普通用户安装入口。

正式发布前的检查重点包括：

- TestPyPI rehearsal 能完整跑通
- PyPI 目标安装命令在干净环境中可用
- extras 安装后的官方插件可被宿主发现
- `modlink-studio` 命令入口正常

## 常见问题

### 为什么文档已经写 PyPI，但当前还不能直接安装 `0.2.0`

因为 `0.2.0` 还未正式发布。当前安装页描述的是目标发布状态，而不是已经完成的发布结果。

### `TestPyPI` 是不是以后长期使用的安装源

不是。`TestPyPI` 只用于发布前 rehearsal；正式发布后，公开安装入口以 PyPI 为准。

### 已安装主应用但看不到某个官方插件

主应用默认不会带上所有官方插件。需要显式安装对应 extra，或在源码工作区里通过根项目 extra 启动。

### 系统里找不到 `modlink-studio` 命令

先确认安装发生在当前 Python 环境中；如果只是临时验证，也可以直接使用 `python -m modlink_studio`。
