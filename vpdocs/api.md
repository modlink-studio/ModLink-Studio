# API 快速索引

这个页面不是完整教程，而是一个快速入口页。

如果你已经知道自己要找什么类型或模块，可以直接从这里跳过去。

## 完整 API 参考

如果你想看从源码 docstring 自动生成的 API 文档，直接跳到 pdoc：

- [打开 pdoc 总览](./pdoc/index.html)

如果你想直接看某个包：

- [modlink_sdk](./pdoc/modlink_sdk.html)
- [modlink_core](./pdoc/modlink_core.html)
- [modlink_ui](./pdoc/modlink_ui.html)
- [modlink_studio](./pdoc/modlink_studio.html)

如果这些链接 404，先重新构建文档站和 pdoc 产物。

## SDK 里最常看的对象

### `Driver`

最通用的 driver 基类。

适合：

- callback 型设备
- 不适合写成固定 `loop()` 的设备
- 比较特殊的接入逻辑

### `LoopDriver`

面向常见轮询型设备的 helper。

适合：

- 串口轮询
- BrainFlow 风格设备
- 一次短循环就能表达的采集逻辑

### `SearchResult`

`search()` 返回的候选对象。

对 host 来说：

- `title` / `subtitle` 用于展示
- `extra` 原样回传给 `connect_device()`

### `StreamDescriptor`

一个 stream 的静态说明。

最常回答的问题是：

- 这个 stream 叫什么
- 这是什么模态
- 这个 payload 应该怎么解释
- `chunk_size` 和通道名是什么

### `FrameEnvelope`

driver 实时发出的数据块。

最常回答的问题是：

- 属于哪个 `stream_id`
- 数据时间戳是什么
- 数据 shape 应该怎么解释

## 如果你还不确定先看哪页

- 想接设备：看 [SDK](/sdk)
- 想理解运行时：看 [Core](/core)
- 想做页面展示：看 [UI](/ui)
- 想知道应用入口怎么挂插件：看 [App](/app)
