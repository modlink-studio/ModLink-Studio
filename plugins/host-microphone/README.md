# Host Microphone Plugin

本插件把本机麦克风输入接入 `ModLink Studio`，并向宿主提供音频波形流。

## 包接口

- 正式分发名：`modlink-plugin-host-microphone`
- 宿主 extra：`official-host-microphone`
- entry point：`host-microphone`

## 适用场景

- 本机音频输入预览
- 音频采集链路联调
- 作为官方示例音频插件进行开发联调

## 从已发布包安装

```bash
python -m pip install \
  --extra-index-url https://dl.cloudsmith.io/public/xylt-space/modlink-studio/python/simple/ \
  "modlink-studio[official-host-microphone]"
```

## 在仓库里联调

```bash
uv run --extra official-host-microphone modlink-studio
```
