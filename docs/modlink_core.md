# ModLink Core 模块架构

`modlink_core` 位于系统架构的最中枢地带，是一个统筹底层硬件协议向外“播撒信号”和对内“强制存盘的”调度服务集群。它没有针对任何一款设备的直接逻辑，但它管辖着全系统数据的命脉流动。

## 1. 核心边界与生态位

它连接着所有的驱动实例（`modlink_drivers`），依赖标准的数据模型（`modlink_shared`）。最后，它将自己包装成一个“引擎黑盒（`ModLinkEngine`）”，抛给 UI 界面（`apps/modlink_studio`）。
它的工作就是**不关心是谁发的数据，只要发出来了，就管教好发信过程、提供正确的订阅，并在必要时把内容序列化到磁盘上。**

## 2. 关键代码行为详解

### `settings/service.py` (`SettingsService`) —— 全局数据配置服务
- **行为本质**：由于在客户端生态存在复杂的 UI 启停或者驱动重配环境状态，它提供了系统内唯一的“JSON 本地磁盘化操作台”。
- **特质**：
  - 它是全局单例，但单例的创建位置被固定在 app 启动入口。后续模块只能通过 `instance()` 访问，不再沿 engine/runtime 传参。
  - 各级组件可借由它的 `instance()` 获取自身对应命名空间前缀数据并独立监听变更事件（`SettingChangedEvent`），而不用中介代理人进行逐层通知过滤。
  - settings 只负责层级键值树，不承载模块专属配置类。模块自己的“设置语义”通过域和 schema 约束表达。
  - 当前域设计约定：
    - `acquisition.storage.*`
    - `drivers.<driver_id>.streams.<stream_id>.*`
    - `ui.*`
  - 如果 `driver_id` 或 `stream_id` 本身包含 `.`，则在 settings key 中必须先转成安全的 key segment，再拼接进路径；不要把原始标识直接拿来 `split('.')`。
  - 当前线程约束：
    - `set/remove/save` 视为主线程行为
    - worker 线程如果需要消费配置，应在自己的生命周期边界读取或通过事件同步，而不是把 service 当成随意跨线程共享容器

### `bus/stream_bus.py` (`StreamBus`) —— 数据神经中枢总线
- **行为本质**：“主题收集墙”加“广播大喇叭”。所有由 Driver 发出的底层活体数据帧，必须在这个集散中心排队。
- **运行细节**：
  1. **注册协议（`register_stream`）**：在系统初始化的几秒内，驱动必须经过 `DriverPortal` 把自己身上的骨骼说明书（`StreamDescriptor`）通过这里注册备案。如果有重名冲撞（比如两个驱动的标识名相同报错退出机制），会在这卡死不允许上发。（比如确保系统里只存在一个活体的 `mock.eeg` 轨道字典）。并自动和发数据的源头信号搭界（`frame_signal.connect(...)`）。
  2. **广播拦截与派发（`publish_frame`）**：每当有 `FrameEnvelope` 的信号涌入，它会再次做一遍安检：如果源头不在早前注册好的名册中，丢弃。然后立刻在当前的 `sig_frame` 管道中往全系统撒这些有效数据包。

### `acquisition/backend.py` (`AcquisitionBackend` & Worker) —— 从高速流到慢速盘的隔离阀
因为向文件硬盘上高速写录制数据极其容易因为底层操作系统 IO 队列写满而吃卡顿（尤其在采集持续了一段时间或者面对巨大采样率阵列的时候），它再次引入了与 `DriverPortal` 如出一辙的主从分离设计：

- **`AcquisitionBackend`（大管家）**：驻守于主线程。负责暴露出给到外部交互按钮的方法，例如按一下采集开始按钮触发 `self.start_recording(...)`。采集根目录等配置并不会在 worker 构造时绑定，而是在每次开始录制时从 settings 读取一次，形成这次 recording 的配置快照。
- **`AcquisitionWorker`（苦力工作者）**：它是真实写硬盘和编解码代码的宿主。
  - 初始化时，通过 `moveToThread` 下沉至专属 `modlink.acquisition` 后台安全舱运行。
  - 直接在安全舱内连通并监听到了 `StreamBus` 涌入的海啸般的 `sig_frame` 原发广播。
  - 通过内部聚合与队列管理落盘对象（如 `RecordingStorage`），它将对传来的 `FrameEnvelope` 切块进行高频存盘。这让前边渲染的波形在前端继续保持丝滑无延迟，不干扰用户体验。

### `runtime/engine.py` (`ModLinkEngine`) —— IoC 控制反转容器聚合者
- **行为本质**：将本文件散落在全局的小物件揉成“功能集成块”用来开机交付给业务 UI。
- **处理步骤**：在实例化这一个对象时：
  1. 它新建自己专属的一套总线服务 `self.bus`。
  2. 它新建依赖此总线的一个存储后端 `self._acquisition`，并启动准备。（相当于拉好了存储接好水管）。`AcquisitionBackend` 会自行从全局 settings 中读取自己的域配置，而不是由 engine 代管。
  3. 它遍历接收在启动入口处给定的散装 `Driver` 列表驱动（如 `MockDriver`），强制给所有新来的驱动上锁并嵌套上防护外衣（穿好线程马甲 `DriverPortal`，交由大总管调度）。并负责最后当程序遭遇终止异常时调用一波清除指令。

## 3. 设计优势与总结
整个 `modlink_core` 实质是提供了一套 **单向数据环流底座设计（Unidirectional Data Flow）** ：

- 底层硬件驱动（`DriverPortal`）被接管启动 → 只会只写不读得向总线里猛灌合法数据帧（`StreamBus`）。
- 外部所有试图截取或存储（如这里的 `AcquisitionBackend` 以及以后的 Plot UI Widget），只能挂靠在 `StreamBus` 上进行事件只读截取，没有倒推回去反写的权利。
- 业务流涉及存取盘则均以独立 `Worker + moveToThread Queued Event` 作为护城河。所有的组件呈现高度“搭积木”感。
