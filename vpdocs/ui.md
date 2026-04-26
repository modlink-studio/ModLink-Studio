# UI 模块架构

当前阶段，桌面 UI 路线已经完全收敛到 widgets 主宿主：

- `modlink_ui`：当前主桌面宿主使用的 Qt Widgets UI 包，内部同时承载 Qt bridge

同时，`modlink_server` 建立的是服务化 host 边界，而不是再去扩展 Qt Widgets 的职责。

## UI 最该依赖什么

写展示页面时，最值得先依赖的是这些稳定字段：

- `stream_id`
- `payload_type`
- `data.shape`
- `channel_names`
- `metadata["unit"]`
- `display_name`

如果这些信息已经稳定，UI 通常也会稳定。UI 最好消费的是统一流模型，而不是某个具体设备自己的协议细节。

## 当前表现层结构

### `modlink_ui`

这是当前主桌面宿主 `modlink_studio` 使用的 UI 包。它承担：

- 主窗口和页面结构
- 设备页、设置页、采集面板
- 现有 Widgets 预览链路

当前版本里它仍然会继续保留，不作为被替代或被删除的旧路径。

### `modlink_server`

`modlink_server` 不是另一套桌面 UI，它承担的是服务化 host 边界。

它当前的意义是：

- 把 backend 暴露为明确的服务宿主
- 固定 `HTTP + SSE + WebSocket` 三条 wire contract
- 为后续 HTML / Web UI 提前建立 host 边界

当前更值得关注的是：

- widgets 桌面 UI
- FastAPI 服务化 host

## 一个合理的 UI 工作顺序

1. 先拿到 `StreamDescriptor`
2. 再决定这个流应该怎么画
3. 再订阅对应 `stream_id`
4. 最后根据 `FrameEnvelope.data` 的 shape 解释实时数据

也就是说，UI 不应该在收到 frame 时临时猜“这是不是 EEG”“这是不是三轴加速度计”；这些信息更适合来自 descriptor。

## 为什么 UI 不该直接依赖设备协议

一旦 UI 直接依赖某个设备 SDK 的特殊字段，后面就很难复用。

例如：

- 如果 UI 直接判断“这是 Ganglion，所以应该有 4 个 EEG 通道”
- 那它就无法自然复用到另一个 EEG 设备

更合理的方式是：

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

因此对 UI 来说，Core 更像“稳定的流提供者”；Qt bridge 的职责是把 runtime 安全地接回 UI 主线程，而不是在 bridge 里定义新的后端语义。

## 推荐阅读

- 接设备：看 [SDK](/sdk)
- 看运行时边界：看 [Core](/core)
- 看宿主装配：看 [App](/app)
- 看服务化接口：看 [服务端 API 手册](/server-api)
