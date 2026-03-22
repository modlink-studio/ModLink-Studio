# SDK 开发者指南

这个页面面向的是要把自己的设备接入 ModLink Studio 的开发者。

如果你只想知道一件事，那就是：

- 常见轮询设备优先考虑 `LoopDriver`
- callback 型设备直接继承 `Driver`

## 快速定位

- [先选哪一个基类](#先选哪一个基类)
- [最小接入流程](#最小接入流程)
- [三个核心数据模型](#三个核心数据模型)
- [driver 生命周期](#driver-生命周期)
- [插件项目怎么组织](#插件项目怎么组织)
- [命名建议](#命名建议)

## 先选哪一个基类

### `Driver`

`Driver` 是最通用的基础契约。

适合这类设备：

- callback 型 SDK
- 比较特殊的第三方库
- 一个固定 `loop` 很难表达清楚的设备

你通常需要自己实现：

- `search()`
- `connect_device()`
- `disconnect_device()`
- `start_streaming()`
- `stop_streaming()`
- `descriptors()`

### `LoopDriver`

`LoopDriver` 是给常见轮询型设备准备的轻量 helper。

适合这类设备：

- 串口轮询
- BrainFlow 这类“查有没有数据，再取数据”的设备
- 自己的协议里天然就是一个短循环的设备

你通常需要实现：

- `search()`
- `connect_device()`
- `disconnect_device()`
- `descriptors()`
- `loop()`

可选实现：

- `on_loop_started()`
- `on_loop_stopped()`
- `loop_interval_ms`

`LoopDriver` 已经满足普通 `Driver` 契约，所以当前 runtime 不需要额外适配它。

## 最小接入流程

不管你最终选哪一个基类，最小接入流程都差不多：

1. 定义一个 driver 类
2. 实现 `device_id`
3. 实现 `descriptors()`
4. 实现 `search()`
5. 实现连接和采集逻辑
6. 通过 `sig_frame` 发出 `FrameEnvelope`

如果你想先把链路跑通，推荐优先把这两件事定住：

- `StreamDescriptor`
- `FrameEnvelope.data` 的 shape

因为这两件事一旦定住，UI、录制和调试路径都会稳定很多。

## 三个核心数据模型

### `SearchResult`

`search()` 返回的是一组 `SearchResult`。

它的职责很简单：

- `title` / `subtitle` 给用户看
- `extra` 给 driver 自己用

宿主不会解析 `extra`，只是把它原样传回 `connect_device()`。

### `StreamDescriptor`

`StreamDescriptor` 描述的是“这个 driver 会发哪些流”。

最常用的字段是：

- `stream_id`
- `modality`
- `payload_type`
- `nominal_sample_rate_hz`
- `chunk_size`
- `channel_names`
- `unit`

注意：

- host 可能在设备连接前就读取 descriptor
- 所以 `descriptors()` 最好不要依赖“必须先连上设备才能知道”的动态状态

### `FrameEnvelope`

`FrameEnvelope` 是 driver 在运行时真正发出的数据块。

你可以把它理解成：

- `stream_id`：这是哪个流
- `timestamp_ns`：这一块数据的时间戳
- `data`：数据本体
- `seq`：可选顺序号

## driver 生命周期

宿主对 driver 的典型调用顺序是：

1. 创建 driver
2. 读取 `device_id` / `display_name`
3. 读取 `descriptors()`
4. 启动 driver worker thread
5. 调 `search()`
6. 调 `connect_device()`
7. 调 `start_streaming()`
8. 后续调 `stop_streaming()` / `disconnect_device()` / `shutdown()`

对 driver 作者来说，最重要的边界是：

- `search()` 是一次性发现
- `connect_device()` 负责建立连接，但不开始实时采集
- `start_streaming()` 负责开始发 `FrameEnvelope`
- `stop_streaming()` 负责停止发流

如果你继承的是 `LoopDriver`，第 7 步里的 `start_streaming()` 已经由基类实现好了，你只需要写 `loop()`。

## `FrameEnvelope.data` 的常见 shape

这个项目当前最常见的是 `line` 类型流。

建议约定：

- `line`: `[channel_count, chunk_size]`

常见例子：

- EEG 多通道数据
- PPG / ECG 多通道数据
- 加速度计 `x/y/z`

同一个设备、同一种模态下的多个 channel，通常应该放在**同一个 stream**里，而不是拆成多个 stream。

## 插件项目怎么组织

当前推荐把具体设备插件放在 `plugins/` 下，每个插件是一个独立项目。

最小结构可以是：

```text
plugins/
└─ your_device/
   ├─ pyproject.toml
   └─ your_device/
      ├─ __init__.py
      ├─ factory.py
      └─ driver.py
```

其中：

- `factory.py` 提供零参数 `create_driver()`
- `pyproject.toml` 里通过 `modlink.drivers` 注册 entry point

当前推荐启动方式不是把插件装进根 workspace，而是运行时临时附加：

```bash
uv sync
uv run --with ./plugins/openbciganglion modlink-studio
```

开发插件时则用：

```bash
uv sync
uv run --with-editable ./plugins/openbciganglion modlink-studio
```

## 命名建议

### `device_id`

建议表达“这是哪个 driver / 哪类设备”，并保持稳定。

例如：

- `eeg:openbci:ganglion`
- `audio:microphone:demo`

### `stream_id`

建议用：

```text
{device_id}:{stream_name}
```

例如：

- `eeg:openbci:ganglion:eeg`
- `audio:microphone:demo:waveform`

## 什么时候不要急着抽新基类

如果你接的是 callback 型设备，先直接继承 `Driver` 往往更干净。

原因很简单：

- `LoopDriver` 的公共模式非常稳定
- callback 型设备的启动、注册和停止方式差异更大

所以当前 SDK 的策略是：

- 对最常见的轮询设备，先提供 `LoopDriver`
- 对 callback 型设备，先保留基础 `Driver`

等真的出现了稳定的 callback 共性，再考虑要不要抽新的 helper。
