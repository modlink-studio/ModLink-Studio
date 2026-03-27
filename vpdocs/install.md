# 安装与发布

本页汇总 ModLink Studio 第一版的安装入口、官方插件安装方式和发布源信息。

## 官方包源

ModLink Studio 的公开 Python 包源位于 Cloudsmith OSS：

```text
https://dl.cloudsmith.io/public/xylt-space/modlink-studio/python/simple/
```

源码与文档入口：

- 源码仓库：[github.com/modlink-studio/ModLink-Studio](https://github.com/modlink-studio/ModLink-Studio)
- 文档站点：[modlink-studio.github.io](https://modlink-studio.github.io)
- Cloudsmith 包源：[dl.cloudsmith.io/public/xylt-space/modlink-studio/python/simple/](https://dl.cloudsmith.io/public/xylt-space/modlink-studio/python/simple/)

## 为什么当前使用 `--extra-index-url`

当前公开 Cloudsmith 仓库没有配置 PyPI upstream proxy。

在这种条件下：

- 使用 `--index-url` 会让解析器只查询 Cloudsmith
- Cloudsmith 仓库中不存在的公开依赖不会自动回退到 PyPI
- 结果是安装 `modlink-studio` 时可能卡在公开依赖解析上

因此当前推荐使用 `--extra-index-url`。这样 `modlink-studio` 和官方插件来自 Cloudsmith，公开依赖继续从 PyPI 解析。

## 安装主应用

```bash
python -m pip install modlink-studio --extra-index-url https://dl.cloudsmith.io/public/xylt-space/modlink-studio/python/simple/
```

## 安装官方插件

第一版官方插件按需安装，不会随主应用一次性全部启用。

可用 extras：

- `official-host-camera`
- `official-host-microphone`
- `official-openbci-ganglion`

安装示例：

```bash
python -m pip install "modlink-studio[official-host-camera]" --extra-index-url https://dl.cloudsmith.io/public/xylt-space/modlink-studio/python/simple/
```

```bash
python -m pip install "modlink-studio[official-host-camera,official-host-microphone]" --extra-index-url https://dl.cloudsmith.io/public/xylt-space/modlink-studio/python/simple/
```

```bash
python -m pip install "modlink-studio[official-openbci-ganglion]" --extra-index-url https://dl.cloudsmith.io/public/xylt-space/modlink-studio/python/simple/
```

## 从源码安装

如果目标是开发、联调或跟进仓库当前实现，可以直接从源码运行，而不是先从 Cloudsmith 安装发布包。

前置要求：

- Python 3.13
- Git

安装 `uv`：

```bash
python -m pip install uv
```

获取源码并同步环境：

```bash
git clone https://github.com/modlink-studio/ModLink-Studio.git
cd ModLink-Studio
uv sync
```

从仓库直接启动宿主：

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

这种方式适合：

- 开发和调试宿主
- 联调官方插件或外部 driver
- 查看当前仓库版本而不是已发布版本

如果只是正常使用宿主应用，仍然更推荐前面的 Cloudsmith 安装方式。

## 运行

安装完成后，正式入口是 GUI script：

```bash
modlink-studio
```

调试入口保留为：

```bash
python -m modlink_studio
```

如果目标是开发独立 driver，脚手架工具也会随主应用一起安装：

```bash
modlink-plugin-scaffold --zh
```

更完整的 driver 开发说明见 [SDK 开发者指南](/sdk)。

## 常见安装问题

### 只使用 `--index-url` 后依赖无法解析

通常说明当前 Cloudsmith 公共仓库没有配置上游代理，而安装命令把 Cloudsmith 当成了唯一索引。请改用本页给出的 `--extra-index-url` 方式。

### 已安装主应用但看不到某个官方插件

主应用默认不会带上所有官方插件。需要显式安装对应 extra，或在仓库内开发时通过根项目 extra 运行。

### 系统里找不到 `modlink-studio` 命令

先确认安装发生在当前 Python 环境中；如果只是临时验证，也可以直接使用 `python -m modlink_studio`。
