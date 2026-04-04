# ModLink Studio

[![Packages on Cloudsmith](https://img.shields.io/badge/packages-Cloudsmith-2A6DF4?logo=cloudsmith&logoColor=white)](https://dl.cloudsmith.io/public/xylt-space/modlink-studio/python/simple/)
[![OSS hosting by Cloudsmith](https://img.shields.io/badge/OSS%20hosting-Cloudsmith-2A6DF4?logo=cloudsmith&logoColor=white)](https://cloudsmith.com/)

面向设备接入、多模态采集与展示的桌面宿主应用。

ModLink Studio 把设备搜索、连接、实时流消费、预览和采集流程统一到同一套运行时里。设备接入者只需要实现 driver 和流描述；宿主应用、录制链路和大部分展示逻辑可以复用同一套平台能力。

当前仓库主线版本是 `0.2.0`。这是一次明确的 breaking change：

- `modlink_sdk` / `modlink_core` 已经切成纯 Python runtime
- `0.2.0` 不兼容 `0.1.x` 的 Qt-style driver API
- UI 仍在适配期；backend 已脱 Qt，但 UI 主线程 bridge 仍是后续工作项

![ModLink Studio screenshot](assets/ui-demo.png)

<details>
  <summary>查看更多界面截图</summary>

  <p>
    <img src="assets/ui-demo2.png" alt="ModLink Studio screenshot 2" />
  </p>
  <p>
    <img src="assets/ui-demo3.png" alt="ModLink Studio screenshot 3" />
  </p>
</details>

## 项目入口

- 源码仓库：[github.com/modlink-studio/ModLink-Studio](https://github.com/modlink-studio/ModLink-Studio)
- 文档站点：[modlink-studio.github.io](https://modlink-studio.github.io)
- 官方包源：[dl.cloudsmith.io/public/xylt-space/modlink-studio/python/simple/](https://dl.cloudsmith.io/public/xylt-space/modlink-studio/python/simple/)

ModLink Studio 的公开包托管由 Cloudsmith OSS 提供支持。安装命令、官方插件分发和发布说明都以 Cloudsmith 仓库 `xylt-space/modlink-studio` 为准。

## 安装

第一版公共包源没有配置 PyPI upstream proxy。  
在这种条件下，如果把 Cloudsmith 直接写成 `--index-url`，解析器只会从 Cloudsmith 查找依赖，找不到的公开依赖也不会回退到 PyPI。当前推荐使用 `--extra-index-url`，让 `modlink-studio` 来自 Cloudsmith，公开依赖继续从 PyPI 解析。

公共安装源：

```text
https://dl.cloudsmith.io/public/xylt-space/modlink-studio/python/simple/
```

安装主应用：

```bash
python -m pip install modlink-studio --extra-index-url https://dl.cloudsmith.io/public/xylt-space/modlink-studio/python/simple/
```

## 官方插件

主应用不会默认安装所有官方插件。第一版官方插件按需通过 extras 安装：

- `official-host-camera`
- `official-host-microphone`
- `official-openbci-ganglion`

正式分发名：

- `modlink-plugin-host-camera`
- `modlink-plugin-host-microphone`
- `modlink-plugin-openbci-ganglion`

对应 entry point：

- `host-camera`
- `host-microphone`
- `openbci-ganglion`

按需安装示例：

```bash
python -m pip install "modlink-studio[official-host-camera]" --extra-index-url https://dl.cloudsmith.io/public/xylt-space/modlink-studio/python/simple/
```

```bash
python -m pip install "modlink-studio[official-host-camera,official-host-microphone]" --extra-index-url https://dl.cloudsmith.io/public/xylt-space/modlink-studio/python/simple/
```

```bash
python -m pip install "modlink-studio[official-openbci-ganglion]" --extra-index-url https://dl.cloudsmith.io/public/xylt-space/modlink-studio/python/simple/
```

## 运行方式

正式用户入口是 GUI script：

```bash
modlink-studio
```

调试和排查时可以使用模块入口：

```bash
python -m modlink_studio
```

## Driver 开发模型

外部独立 driver 项目应当依赖最小公共接口，而不是依赖宿主应用本身。当前推荐的依赖模型是：

- `modlink-sdk`
- 设备自身的传输层依赖

只有在确实需要运行时服务时，才额外依赖 `modlink-core`。driver 安装到与宿主相同的 Python 环境后，会通过 `modlink.drivers` entry point 被宿主发现。

如果是新建 driver 项目，可以使用独立发布的脚手架工具。它位于仓库的 `tools/` 目录中，不再作为 `modlink-studio` 的运行时依赖自动安装。

```bash
npx @modlink-studio/plugin-scaffold --zh
```

仓库内开发调试时也可以直接跑 workspace：

```bash
npm install
npm --workspace @modlink-studio/plugin-scaffold run dev -- --zh
```

这个工具会交互式生成一个可启动的 driver 项目骨架，通常会包括：

- `pyproject.toml`
- `README.md`
- `LICENSE`
- `.gitignore`
- `<plugin_name>/driver.py`
- `<plugin_name>/factory.py`
- `<plugin_name>/__init__.py`
- `tests/test_smoke.py`

脚手架的作用不是替你实现设备协议，而是先把项目结构、entry point、基础类选择和 stream 描述骨架搭出来，让你从“补真实搜索、连接和发帧逻辑”开始，而不是从零写包结构。

一个最小 `pyproject.toml` 示例：

```toml
[project]
name = "my-driver"
version = "0.2.0"
dependencies = [
  "modlink-sdk",
  "numpy>=2.3.3",
]

[project.entry-points."modlink.drivers"]
my-driver = "my_driver.factory:create_driver"
```

宿主对 driver 保持 fail-fast 策略。坏掉的 entry point、损坏的 driver 或未知 payload 类型都会直接暴露错误，避免把协议错误隐藏成不确定的运行时行为。

## 仓库结构

```text
modlink-studio/
├─ apps/
│  ├─ modlink_studio/
│  ├─ modlink_studio_qml/
│  └─ modlink_server/
├─ packages/
│  ├─ modlink_sdk/
│  ├─ modlink_core/
│  ├─ modlink_ui/
│  └─ modlink_new_ui/
├─ tools/
│  └─ modlink_plugin_scaffold/
├─ plugins/
├─ vpdocs/
└─ deprecated/
```

- `apps/modlink_studio/`: 主应用入口
- `apps/modlink_studio_qml/`: QML 应用入口
- `apps/modlink_server/`: 服务端入口
- `packages/modlink_sdk/`: 对外稳定的最小 SDK 契约
- `packages/modlink_core/`: 纯 Python runtime、流总线和采集基础设施
- `packages/modlink_ui/`: Qt UI 组件和页面
- `packages/modlink_new_ui/`: QML UI
- `tools/modlink_plugin_scaffold/`: 独立 npm driver 脚手架工具
- `plugins/`: 官方插件源目录
- `vpdocs/`: VitePress 文档站源码

## 面向仓库贡献者

仓库内开发使用 `uv`：

```bash
uv sync
uv run modlink-studio
```

从 monorepo 根目录按需附加官方插件：

```bash
uv run --extra official-host-camera modlink-studio
```

```bash
uv run --extra official-host-camera --extra official-host-microphone modlink-studio
```

## 文档与版本

项目文档使用 VitePress，源码位于 `vpdocs/`，站点发布到 `https://modlink-studio.github.io`。

本地预览：

```bash
npm ci
npm run docs:vp:dev
```

构建文档：

```bash
npm ci
npm run docs:pdoc:build
npm run docs:vp:build
```

## 许可证与托管

当前仓库整体按 `GPL-3.0-or-later` 路线发布。详细条款见根目录 [LICENSE](LICENSE)。

ModLink Studio 的公开包由 Cloudsmith OSS 托管。文档站用于说明源码和使用方式；真正的 Python 包安装入口以 Cloudsmith 仓库 `xylt-space/modlink-studio` 为准。
