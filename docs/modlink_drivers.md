# ModLink Drivers 模块架构

`modlink_drivers` 是整个应用与真实硬件/设备通讯的**边界与防腐层**。它的设计理念非常清晰：必须把易阻塞（IO/蓝牙/串口阻塞等）的生硬业务逻辑，安全地隔离并在 PyQt6 线程体系中驯化成事件驱动数据流，而不干扰界面或其他采集并发工作。

## 1. 核心边界与生态位

- **生态位**：它是设备接入的规范书。当未来有新的穿戴式设备或脑电帽接入时，开发者只需在这个模块下基于接口继承编写即可。
- **与应用隔离**：它依赖于基础数据契约 `modlink_shared`（向外发车）与 PyQt6（利用信号）。但它**绝对不依赖于**核心总线（Bus）或采集后端。它是被拔高的纯驱动实现。
- **与插件发现的关系**：第三方 driver component 当前约定通过 `entry_points` 的 `modlink.drivers` 分组暴露给宿主。entry point 应该解析成一个零参数工厂函数；宿主先收集这些工厂，再在组合根里显式调用它们得到 `Driver` 实例，而不是直接暴露一个已构造好的实例。
- **与 settings 的关系**：driver 不再依赖专属 `XxxDriverSettings` 配置类，而是通过全局 `SettingsService` 的域路径读取自己的启动配置。当前约定路径为：
  - `drivers.<driver_id>.streams.<stream_id>.chunk_size`
  - `drivers.<driver_id>.streams.<stream_id>.nominal_sample_rate_hz`
  - 若 `driver_id` / `stream_id` 自身包含 `.`，则必须先转成 settings-safe segment 再作为路径组件使用。

## 2. 关键代码行为详解

### `base.py` —— 接口与边界定义
这是所有具体硬件交互的协议基座。

```python
class Driver(QObject):
    sig_event = pyqtSignal(object)
    ...
```
- **核心行为**：
  - 强制继承 `QObject` 并持有一个广义的信号出口 `sig_event`。这个信号未来用来发出宽泛的如硬件重连、电池没电、固件搜索完成等杂项事件字典。
  - **规范化动作槽口**：对外的生命周期全部被锁死在 `search(...)`, `connect_device(...)`, `disconnect_device()`, `start_streaming()`, `stop_streaming()` 这几个方法中。任何人写新驱动，必须覆盖它们去实现对应的控制指令或线程循环启停。
  - **宿主管理约束**：driver 一旦被 `DriverPortal` 接管，就不允许再被第二个 portal 重复接管。换句话说，driver component 是应用级稳定组件，但生命周期动作权只属于宿主框架。
  - **初始化约束**：如果 driver 通过 entry point 暴露工厂函数，那么工厂函数和 `__init__` 都必须保持轻量，不允许在导入阶段直接连接硬件、启动线程或开始 streaming。

- **为什么不强制写死类型枚举事件？**  
  在产品打样与 UI 连接阶段，驱动传出来的事件极其零散无法预测（有可能是 `kind="disconnected"` 也有可能是 `battery_low`），利用底座约束事件流的开口位置，采用鸭子类型/字典宽泛约束便于开发者应对不可知的底层固件状况。

### `portal.py` —— 跨线程边界的代理管家
它是**整个驱动模块设计中最精彩的部分 (防腐层 + 隔离层)**。任何系统内部成员（比如：ModLinkEngine 或 UI 的开始按键），从来不会也不被允许直接触碰真实的 `Driver` 实例，而是碰这个 `DriverPortal` 代理。

#### 主要行为与机制：
- **子线程封装转移 (`moveToThread`)**：
  在 `__init__` 中，它创建一条针对该特定设备的独立子线程（`QThread(self, thread_name="modlink.driver.xxx")`）。然后，利用了 Qt 霸道的 `moveToThread` 语法，把外界丢给它的原生 `driver` 塞进了这条黑屋子线程。从这之后，`driver` 所有的流阻塞与数据发射均在异步中执行，这保障了 UI 线程即使在尝试蓝牙搜索死锁的情况下，依旧能流畅刷新 60 帧页面。
  
- **安全请求派发 (QueuedConnection 化)**：
  ```python
  _request_start_streaming = pyqtSignal()
  ...
  self._request_start_streaming.connect(
      self._driver.start_streaming,
      Qt.ConnectionType.QueuedConnection,
  )
  ```
  外部试图去启动流（如直接调用 `portal.start_streaming()`时），Portal 其内部绝不会同步调用驱动对象，而是 `emit` 自己身上的私有信号，这个信号顺着 Qt 的事件列队（Queued）被扔去了驱动所在的子线程再执行对应的目标动作。

- **事件聚合转发**：它负责将下属的真实 `Driver` 的流产信息再包一层（加上自己的 `driver_id` 和时间戳），然后投到引擎可见的光明世界中：`DriverEvent(driver_id, event, ts)`。

### `discovery.py` —— entry point 驱动发现
- **行为本质**：它是第三方 driver component 进入系统的唯一推荐入口，当前约定的 entry point group 为 `modlink.drivers`。
- **加载规则**：
  - discovery 先解析出零参数工厂函数
  - 组合根再调用这些工厂函数得到 `Driver` 实例
  - `device_id` 不能为空
  - 同一轮发现中不允许出现重复的 `device_id`
- **设计意图**：宿主拿到的是稳定的应用级 driver component，然后再交给 `DriverPortal` 托管其线程与动作生命周期；插件自己不拥有“私自启动”的权利。

### `minimal.py` / `sources.py` / `chunking.py` —— 最小 driver 范本
- **`MinimalDriver` 的行为**：
  它现在故意只保留 driver 契约本身必须承担的工作：声明 `device_id` / `display_name` / `descriptors()`，实现 `search(...)`、`connect_device(...)`、`disconnect_device()`、`start_streaming()`、`stop_streaming()` 这些生命周期槽口，并把下游 source 发来的 `FrameEnvelope` 转发到框架总线。
- **`sources.py` 的行为**：
  真实的数据采集逻辑被拆到了 `FrameSource` 抽象下面。当前仓库提供的 `MicrophoneFrameSource` 用系统默认麦克风作为真实输入，通过 `QAudioSource` 读取 PCM 音频，按固定 chunk 切片后包装成 `FrameEnvelope`。这意味着后续设备接入者如果想写自己的 driver，可以优先模仿 source 的部分，把“怎么读设备数据”单独隔离出来，而不是把采数循环和 driver 生命周期全部搅在一起。
- **为什么这样更适合作为范本**：
  设备接入者看 `minimal.py` 时，看到的是“接入 ModLink 平台最少要履行哪些职责”；看 `sources.py` 时，看到的是“如果你要接真实世界的数据源，采数代码应该放在哪”。两者解耦以后，`mock data` 和 `real data` 都可以复用同一个 driver 外壳。
- **`chunking.py` 的作用**：在真实设备收集中，底层数据常常不是按平台希望的 chunk 直接到达。`chunking.py` 保留了 chunk 时间和采样率的公共换算逻辑，用来把底层的字节流或单点样本整理成稳定的二维 Numpy 数据块。
- **当前 driver 设置设计**：
  - stream 级参数通过 settings 域读取，而不是通过 driver 专用 settings dataclass
  - `driver_id` 是 settings 域的实例级命名空间
  - `stream_id` 是其下的子域
  - `chunk_size` 与 `nominal_sample_rate_hz` 已经是 `StreamDescriptor` 的正式字段，但当前仍然视为启动期配置；如果需要运行时热改，必须同时解决 descriptor 更新问题

## 3. 设计优势与总结

1. **消解死锁风险**：对于一切与物理世界连线的代码，极容易面临 IO Block（IO 阻塞拦截）。如果直接把读取流暴露在程序的生命周期里，主线程一定会死机。`DriverPortal` 将管理和隔离下放了，从全局视角来看，这相当于为每个设备分配了一个“无头沙盒”。
2. **测试性高**：由于在 `Driver` 基类本身，不用手搓多线程 Worker （全部交给 Portal），它就是一个只管接受状态机调用然后读数的傻瓜体，极其容易写纯逻辑黑盒测试（传参数 → 获得假的包）。
