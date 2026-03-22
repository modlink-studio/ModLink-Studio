# UI 模块架构

UI 层面对的是“已经进入系统的流”，而不是“设备底层协议”。

这页最重要的一句话是：

- UI 应该依赖 `StreamDescriptor` 和 `FrameEnvelope`，不要直接依赖某个具体设备的连接细节

## UI 最应该关心什么

写展示页面时，通常最值得先看的是：

- `stream_id`
- `payload_type`
- `data.shape`
- `channel_names`
- `unit`
- `display_name`

如果这几件事已经稳定，UI 通常就能稳定。

## 一个合理的 UI 工作顺序

推荐的顺序是：

1. 先拿到 `StreamDescriptor`
2. 再决定这个流应该怎么画
3. 再订阅对应 `stream_id`
4. 最后根据 `FrameEnvelope.data` 的 shape 解释实时数据

也就是说，UI 不应该在收到 frame 时临时猜“这是不是 EEG”“这是不是三轴加速度计”，这些信息应该尽量来自 descriptor。

## 一个 stream 通常对应什么

在当前项目里，一个 stream 通常对应一个“稳定的展示面板”。

例如：

- 一个 EEG stream 对应一个多通道波形面板
- 一个加速度计 stream 对应一个三轴面板
- 一个音频波形 stream 对应一个波形视图

同一个 stream 下的多个 channel，通常应该被理解成：

- 同一块数据里的多个通道
- 同一个面板里的多条曲线或多个子轨道

而不是多个完全无关的 stream。

## 为什么 UI 不该直接依赖设备协议

因为 UI 一旦直接依赖某个设备 SDK 的特殊字段，后面会很难复用。

举个例子：

- 如果 UI 直接判断“这是 Ganglion，所以应该有 4 个 EEG 通道”
- 那它就无法自然复用到另一个 EEG 设备

更好的方式是：

- UI 只读 `StreamDescriptor.channel_names`
- UI 只读 `payload_type`
- UI 只解释统一的 `FrameEnvelope.data`

这样换一个设备，只要 descriptor 和 data shape 还守同一套约定，UI 就能继续工作。

## UI 和 Core 的边界

UI 通常不需要知道：

- driver 跑在哪条线程上
- 设备怎么搜索
- 设备怎么连接
- 流是 callback 还是 loop 驱动的

UI 真正需要知道的是：

- 这个流叫什么
- 这个流怎么解释
- 什么时候有新数据

所以对 UI 开发者来说，Core 更像“稳定的流提供者”，而不是“必须深入理解的内部系统”。

## 当前最值得依赖的稳定字段

如果你想让页面尽量通用，建议优先依赖这些字段：

- `descriptor.stream_id`
- `descriptor.payload_type`
- `descriptor.channel_names`
- `descriptor.unit`
- `frame.data`

其中：

- `channel_names` 和 `unit` 已经比随意塞到 `metadata` 里更适合做共享约定
- `metadata` 更适合做补充信息，而不是做 UI 主逻辑的唯一依据

## 推荐阅读

- 接设备的人：看 [SDK](/sdk)
- 看运行时边界的人：看 [Core](/core)
- 看应用如何挂页面的人：看 [App](/app)
