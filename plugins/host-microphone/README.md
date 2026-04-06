# Host Microphone Driver

本驱动把本机麦克风输入接入 `ModLink Studio`，并向宿主提供音频波形流。

## 接入方式

- 内置于 `modlink-studio` 主包
- 宿主 extra：`official-host-microphone`
- entry point：`host-microphone`

## 适用场景

- 本机音频输入预览
- 音频采集链路联调
- 作为官方示例音频驱动进行开发联调

## 启用依赖

```bash
python -m pip install "modlink-studio[official-host-microphone]"
```

## 在仓库里联调

```bash
uv run --extra official-host-microphone modlink-studio
```
