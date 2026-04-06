# Host Microphone Driver

本驱动把本机麦克风输入接入 `ModLink Studio`，并向宿主提供音频波形流。

## 接入方式

- 通过 `modlink-studio-plugin install host-microphone` 安装到当前环境
- entry point：`host-microphone`

## 适用场景

- 本机音频输入预览
- 音频采集链路联调
- 作为官方示例音频驱动进行开发联调

## 安装方式

```bash
modlink-studio-plugin install host-microphone
```

## 在仓库里联调

```bash
uv run python -m pip install -e plugins/host-microphone
```
