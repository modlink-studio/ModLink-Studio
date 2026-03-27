# OpenBCI Ganglion Plugin

本插件把 OpenBCI Ganglion 设备接入 `ModLink Studio`，并向宿主提供 EEG `signal` 流。

## 包接口

- 正式分发名：`modlink-plugin-openbci-ganglion`
- 宿主 extra：`official-openbci-ganglion`
- entry point：`openbci-ganglion`

## 当前能力

- 通过 `modlink.drivers` entry point 被宿主发现
- `search()` 支持 `ble` 和 `serial`
- `LoopDriver` 负责基于 runtime 周期调度的轮询和流生命周期
- 输出固定 chunk 的 EEG `signal` payload

当前插件实现已经跟随 `0.2.0` 主线迁移到纯 Python runtime，不再依赖 Qt signal 或 `QTimer`。

## 适用场景

- OpenBCI Ganglion EEG 接入
- 官方 BrainFlow 轮询式 driver 示例
- EEG 预览和采集流程联调

## 从已发布包安装

```bash
python -m pip install "modlink-studio[official-openbci-ganglion]" --extra-index-url https://dl.cloudsmith.io/public/xylt-space/modlink-studio/python/simple/
```

## 在仓库里联调

```bash
uv run --extra official-openbci-ganglion modlink-studio
```
