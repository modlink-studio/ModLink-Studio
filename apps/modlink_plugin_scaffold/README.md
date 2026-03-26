# Plugin Scaffold CLI

`modlink-plugin-scaffold` 是官方提供的 driver 脚手架工具，第一版会随 `modlink-studio` 一起安装。

在仓库里运行：

```bash
uv run modlink-plugin-scaffold --zh
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

生成项目对外发布前，建议补齐两类项目元数据：

- 该 driver 自己的 README
- 该 driver 自己的 LICENSE 与项目链接
