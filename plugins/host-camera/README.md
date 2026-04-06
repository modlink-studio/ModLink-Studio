# Host Camera Driver

本驱动把本机内置或外接摄像头接入 `ModLink Studio`，并向宿主提供视频流。

## 接入方式

- 内置于 `modlink-studio` 主包
- 宿主 extra：`official-host-camera`
- entry point：`host-camera`

## 适用场景

- 本机摄像头预览
- 视频流接入与录制
- 作为官方示例视频驱动进行开发联调

## 启用依赖

```bash
python -m pip install "modlink-studio[official-host-camera]"
```

## 在仓库里联调

```bash
uv run --extra official-host-camera modlink-studio
```
