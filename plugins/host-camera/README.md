# Host Camera Plugin

本插件把本机内置或外接摄像头接入 `ModLink Studio`，并向宿主提供视频流。

## 包接口

- 正式分发名：`modlink-plugin-host-camera`
- 宿主 extra：`official-host-camera`
- entry point：`host-camera`

## 适用场景

- 本机摄像头预览
- 视频流接入与录制
- 作为官方示例视频插件进行开发联调

## 从已发布包安装

```bash
python -m pip install "modlink-studio[official-host-camera]" --extra-index-url https://dl.cloudsmith.io/public/xylt-space/modlink-studio/python/simple/
```

## 在仓库里联调

```bash
uv run --extra official-host-camera modlink-studio
```
