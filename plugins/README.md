# 驱动源目录

`plugins/` 保存的是插件源目录；当前仓库里主要是官方驱动源码，不是最终用户的独立 PyPI 安装入口。

从 `0.2.0` 开始，这些插件不会作为独立 PyPI 包公开发布，也不会直接内置到 `modlink-studio` wheel 中。正式安装路径是：

- 先安装 `modlink-studio`
- 再运行 `modlink-plugin install <plugin_id>` 从 GitHub Pages 插件索引解析版本，并从 GitHub Release 安装对应插件 wheel

仓库里的这些目录主要用于开发、联调和 GitHub Release 资产构建。

当前仓库主线是 `0.2.0`。这里的官方驱动也已经按新的纯 Python driver API 迁移，不再以 Qt-style runtime 契约为准。

## 当前官方驱动

- `host-camera/`
  官方驱动源码：Host Camera
- `host-microphone/`
  官方驱动源码：Host Microphone
- `openbci-ganglion/`
  官方驱动源码：OpenBCI Ganglion

## 仓库内联调

从 monorepo 根目录运行时，可以把某个驱动源码直接装进当前环境：

```bash
uv run python -m pip install -e plugins/host-camera
```

```bash
uv run python -m pip install -e plugins/host-microphone
```

```bash
uv run python -m pip install -e plugins/openbci-ganglion
```
