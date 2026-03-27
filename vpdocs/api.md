# API 快速索引

这个页面主要作为 API 入口和 SDK 对象速查表。

如果目标是安装和运行宿主应用，建议先看 [安装与发布](/install)；如果目标是开发 driver，建议先看 [SDK 开发者指南](/sdk)。

如果目标已经比较明确，可以直接从这里跳到对应类型或对应包的 API 页面；如果只是想先看“接一个 driver 到底要碰哪些对象”，建议先读下面这部分。

当前 API 说明以 `0.2.0` 为准：`modlink_sdk` / `modlink_core` 已是纯 Python runtime，`0.2.0` 不兼容 `0.1.x` 的 Qt-style driver API。

## 完整 API 参考

从源码 docstring 自动生成的 API 文档入口如下：

- <a href="/pdoc/index.html" target="_self">打开 pdoc 总览</a>

各个主要包的入口如下：

- <a href="/pdoc/modlink_sdk.html" target="_self">modlink_sdk</a>
- <a href="/pdoc/modlink_core.html" target="_self">modlink_core</a>
- <a href="/pdoc/modlink_ui.html" target="_self">modlink_ui</a>
- <a href="/pdoc/modlink_studio.html" target="_self">modlink_studio</a>

## 先建立一条最小接入链路

从 SDK 视角看，一个 driver 的最小工作链路通常是：

1. 宿主创建一个 `Driver` 或 `LoopDriver` 实例
2. 宿主调用 `bind(context)`，注入 `DriverContext`
3. 宿主调用 `descriptors()`，读取这个 driver 会暴露哪些 `StreamDescriptor`
4. 宿主调用 `search()`，拿到一组 `SearchResult`
5. 宿主把选中的 `SearchResult` 传回 `connect_device()`
6. driver 开始流并提供实时数据后，通过 `emit_frame()` 发出 `FrameEnvelope`
7. 每个 `FrameEnvelope` 都必须能够对应到前面声明过的某个 `StreamDescriptor`

如果这条链路里有一环没有定义清楚，宿主、录制和 UI 就很难稳定工作。因此更需要优先明确的不是“页面长什么样”，而是：

- 这个 driver 有哪些 stream
- 每个 stream 的 `payload_type` 是什么
- 每次发出的 `FrameEnvelope.data` shape 应该怎么解释

## SDK 里最常看的对象

### `Driver`

`Driver` 是所有 driver 的根基类，也是最保守、最通用的起点。

它定义的不是某种具体采集方式，而是一套宿主能理解的统一生命周期：

- `descriptors()`：声明这个 driver 会发哪些流
- `search()`：发现可连接的候选设备
- `connect_device()` / `disconnect_device()`：建立和释放连接
- `start_streaming()` / `stop_streaming()`：开始和停止实时数据流
- `bind(context)`：接入宿主提供的 `DriverContext`
- `emit_frame()`：把 `FrameEnvelope` 发给宿主

适合直接继承 `Driver` 的情况：

- 设备 SDK 本身是 callback 型
- 第三方库会自己推数据过来
- 采集逻辑不适合表达成一个固定频率的短轮询
- 你暂时还不确定轮询模型是否真的合适

如果暂时无法判断，默认回到 `Driver`。`Driver` 的抽象更直接，也更不容易把设备本身的逻辑勉强套进并不合适的轮询模型里。

### `LoopDriver`

`LoopDriver` 的基类也是 `Driver`。它不是另一套独立协议，只是在 `Driver` 之上，为“需要轮询获取数据”的那类设备封装了一个现成的 helper。

它主要帮你做了两件事：

- 把 `start_streaming()` / `stop_streaming()` 包装成由 runtime 周期调度的循环
- 给你一个 `loop()` 钩子，让你只需要写“一次短轮询里做什么”

通常子类只需要：

- 像普通 `Driver` 一样实现 `descriptors()`、`search()`、`connect_device()`、`disconnect_device()`
- 实现 `loop()`
- 按需调整 `loop_interval_ms`
- 按需实现 `on_loop_started()` / `on_loop_stopped()`

适合使用 `LoopDriver` 的情况：

- 串口轮询
- BrainFlow 风格设备
- 一次短循环就能表达清楚的采集逻辑
- “检查是否有新数据，再取出并发帧” 这一类模式

不适合的情况也需要明确：

- 回调型 SDK
- 单次调用会长时间阻塞的读取逻辑
- 需要复杂状态机才能驱动的采集流程

还不确定时，优先回到 `Driver`。`LoopDriver` 是对轮询型设备的便利封装，不是所有 driver 都该往这个模型上靠。

### `SearchResult`

`SearchResult` 是 `search()` 返回的候选设备对象。它的职责很具体：让宿主能展示搜索结果，并在用户选中后把必要配置原样带回 `connect_device()`。

最常用字段：

- `title`：列表主标题
- `subtitle`：列表副标题
- `extra`：driver 自己定义的连接参数

可选补充字段：

- `device_id`：driver 提供的稳定设备标识

这里最重要的边界是：宿主不会解析 `extra` 的内部结构。它只负责展示 `title` / `subtitle`，然后把整个 `SearchResult` 回传给 `connect_device()`。因此你可以把端口号、地址、序列号、传输参数等信息放进 `extra`，由 driver 自己消费。`device_id` 也不是宿主当前会消费的字段；它不是必填项，只有在 driver 希望额外提供设备标识时才需要提供。

### `StreamDescriptor`

`StreamDescriptor` 描述的是“这个 driver 会发出什么流”，它是静态契约，不是实时数据。

宿主可能会在设备连接前就读取 `descriptors()`，所以 `StreamDescriptor` 里写的内容应该在 driver 生命周期内保持稳定。

写 `StreamDescriptor` 时，至少要把这几件事讲清楚：

- `device_id`：这个流属于哪个设备实例，并参与 `stream_id` 派生
- `modality`：这是哪一类模态，并参与 `stream_id` 派生
- `payload_type`：只能从 `signal`、`raster`、`field`、`video` 中选择，它决定预览和录制链路如何解释 `FrameEnvelope.data`
- `nominal_sample_rate_hz`：正数，决定名义采样率相关行为
- `chunk_size`：正整数，录制链路会校验它是否和实际 frame 一致；高采样率设备通常适合更大的 `chunk_size`
- `channel_names`：通道标签；如果数量和实际通道数一致，预览与录制会直接使用
- `display_name`：界面显示名；缺失时通常回退到 `stream_id`
- `metadata`：补充但稳定的说明信息；其中 `unit` 不和 `signal` 绑定，只要流本身有明确量纲就可以填写，它当前会进入录制元数据，并显示在预览摘要中

还需要明确两个关系：

- `stream_id` 不是手写的，而是由 `device_id + modality` 派生出来的稳定标识
- `FrameEnvelope` 的 `stream_id` 必须和这里声明过的某个流对应上

如果从 SDK 接入角度只保留一个重点，那就是：`StreamDescriptor` 决定了宿主如何理解后续的实时数据。这个对象定义不清，后面的 UI、录制和调试都会变得混乱。

### `FrameEnvelope`

`FrameEnvelope` 是 driver 在运行时真正发出的数据块。前面的 `StreamDescriptor` 负责“声明”，`FrameEnvelope` 负责“兑现”这个声明。

每次发帧时，最关键的是下面这些字段：

- `device_id`
- `modality`
- `timestamp_ns`
- `data`
- `seq`
- `extra`

其中有三个实际约束最重要：

1. `device_id + modality` 会派生出 `stream_id`，它必须能对应到某个 `StreamDescriptor`
2. `data` 的 shape 必须和该 `StreamDescriptor` 的约定一致
3. `timestamp_ns` 应该由 driver 提供真实时间语义，而不是随意填一个占位值

可以把它理解成一句话：`StreamDescriptor` 说明“我会发什么”，`FrameEnvelope` 说明“我现在真的发了这一块数据”。

## 继续阅读的入口

- 想接设备：看 [SDK](/sdk)
- 想理解运行时：看 [Core](/core)
- 想做页面展示：看 [UI](/ui)
- 想知道应用入口怎么挂插件：看 [App](/app)
