# 安装与发布

本页汇总 `0.3.0rc1` 的安装目标、官方驱动安装方式和源码运行方式。

## 0.3.0rc1 发布状态

`0.3.0rc1` 当前处于预发布收口阶段：

- `0.3.0rc1` 是 `0.3.0` 的首个 release candidate
- 正式公开发布渠道为 **PyPI**
- **TestPyPI rehearsal** 已完成
- `TestPyPI` 只用于发布链路演练，不作为日常安装源
- 当前仓库版本已切到 `0.3.0rc1`

## 0.3.0rc1 升级说明

`0.3.0rc1` 继续沿用 `0.2.0` 建立的纯 Python runtime 基线：

- `modlink_sdk` / `modlink_core` 已不再依赖 Qt 运行时
- 外部 driver 不再以 `sig_frame` / `sig_connection_lost` 作为正式宿主契约
- `LoopDriver` 不再基于 `QTimer`
- 如果你手头还有 `0.1.x` 的 Qt-style driver，需要按新的 SDK 契约迁移

当前 UI 仍在适配期，但 backend 已经完成去 Qt 化；`0.3.0rc1` 重点增加 recording replay、analysis export 和外部插件 author skill。

## 预发布安装命令

`0.3.0rc1` 是预发布版本，安装时建议明确指定版本：

```bash
python -m pip install --pre modlink-studio==0.3.0rc1
```

安装完成后，正式入口是：

```bash
modlink-studio
```

调试入口保留为：

```bash
python -m modlink_studio
```

## 安装插件

插件不通过 PyPI extras 安装。主包安装完成后使用独立插件管理命令；命令会先从 `ModLink-Studio-Plugins` 的 GitHub Pages 插件索引读取可用版本，再从该插件仓库的 GitHub Release 安装对应插件 wheel。

当前第一阶段，这个命令集主要覆盖官方驱动；后续会继续扩展成更通用的插件管理工具：

```bash
modlink-plugin list
```

```bash
modlink-plugin install host-camera
```

```bash
modlink-plugin install host-microphone
```

```bash
modlink-plugin install openbci-ganglion
```

如果不再需要某个插件：

```bash
modlink-plugin uninstall host-camera
```

如果想看当前环境里已经安装了哪些 ModLink 插件：

```bash
modlink-plugin list --installed
```

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

如果要带控制台和调试日志启动：

```bash
uv run modlink-studio-debug
```

## 外部插件开发

0.3.0rc1 不再提供独立 npm driver 脚手架。外部插件项目建议使用 `tools/modlink-plugin-author/SKILL.md` 作为 Claude Code / Codex 的可分发 skill，在插件自己的仓库里生成和维护 driver 代码。

推荐使用方式是在外部插件项目目录启动 coding agent，把这个 `SKILL.md` 作为 skill 或上下文加载，然后直接描述设备、连接方式、数据流类型和采样率。生成后仍应在插件项目内运行 `python -m pip install -e .` 和测试命令验证。

更完整的 driver 开发说明见 [SDK 开发者指南](/sdk)。

## 发布前验证

`0.3.0rc1` 的 **TestPyPI rehearsal** 已完成。这一步只用于验证发布链路和安装命令，不作为普通用户安装入口。

正式发布前的检查重点包括：

- TestPyPI rehearsal 已完整跑通
- PyPI 目标安装命令在干净环境中可用
- 插件安装 CLI 可从 GitHub Pages 插件索引解析兼容版本，并从 GitHub Release 获取 wheel
- `modlink-studio` 命令入口正常

## 常见问题

### 为什么文档已经写 PyPI，但有时还搜不到最新版本

PyPI 项目页、镜像或本地索引有时会有短暂同步延迟。遇到这种情况时，以 PyPI 项目页和 `pip` / `uv pip` 的实际解析结果为准，稍后重试通常即可恢复正常。

### `TestPyPI` 是不是以后长期使用的安装源

不是。`TestPyPI` 只用于发布前 rehearsal；公开安装入口以 PyPI 为准。

### 已安装主应用但看不到某个插件

主应用不会默认安装所有插件。当前第一阶段主要是官方驱动，需要显式运行 `modlink-plugin install <plugin_id>`；官方驱动源码与 wheel 资产已经迁移到独立仓库 `ModLink-Studio-Plugins`。

### 系统里找不到 `modlink-studio` 命令

先确认安装发生在当前 Python 环境中；如果只是临时验证，也可以直接使用 `python -m modlink_studio`。
