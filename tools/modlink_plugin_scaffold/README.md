# Plugin Scaffold CLI

`modlink-plugin-scaffold` 是官方提供的独立 driver 脚手架工具。它位于仓库的 `tools/` 目录中，不再作为 `modlink-studio` 的运行时依赖自动安装。

当前脚手架默认生成的是 `0.2.0` 风格 driver：宿主契约以纯 Python runtime 为准，不再依赖 Qt-style `sig_frame` / `QTimer` 写法。

在仓库里运行：

```bash
uv run --package modlink-plugin-scaffold modlink-plugin-scaffold --zh
```

安装后的正式入口：

```bash
modlink-plugin-scaffold --zh
```

生成出的 driver 项目应当最小依赖 `modlink-sdk`，然后通过常规 `pip` 安装到和宿主相同的环境：

```bash
python -m pip install -e ./my_driver
python -m modlink_studio
```

生成后的 `driver.py` 会直接给出 `emit_frame()` 等 helper，建议在真实设备接入时沿着这套 callback/context 模型继续补完。

生成项目对外发布前，建议补齐两类项目元数据：

- 该 driver 自己的 README
- 该 driver 自己的 LICENSE 与项目链接
