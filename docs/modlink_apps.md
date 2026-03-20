# App 运行时级与组合根架构

在 `app` 层中包含了 `modlink_studio` 的入口 `app.py` 及针对开放硬件设计的专属 UI 套件（如 `openbciganglionui`）。它们负责将底层引擎拼装起来，并将其以面向用户的可视化形态进行展示和控制操作。

## 1. 核心边界与生态位
它是所有依赖的最终汇聚点，即“组合根（Composition Root）”。整个系统在此之前都是各自并列的组件或是受约束的类原型，只有在这里才会注入实体（例如把指定的驱动对象丢给引擎平台），并负责拉起整个操作系统的图形化事件死循环以维持软件生命。

## 2. 关键代码行为详解

### `apps/modlink_studio/app.py` —— 服务拼盘构建员（入口层）

- **基础设施预载 (`SettingsService(parent=app)`)**：
  在程序最一开始拉起 `QCoreApplication` 后，便首先把配置中心唤醒。这是一个明确的启动约束：应用入口只创建一次 `SettingsService`，后续所有模块只通过 `SettingsService.instance()` 取用，不再把 settings 沿构造参数逐层传递。
  它承担的是“全局层级键值树”职责，而不是具体业务配置类工厂。

- **驱动发现启动 (`discover_driver_factories()`)**：
  在 settings 单例就位后，app 会扫描 `modlink.drivers` entry point 分组，收集零参数工厂函数，再在组合根里显式实例化 `Driver`，最后统一交给 `ModLinkEngine`。这样 driver component 的进入位置是固定的，宿主拥有唯一的生命周期控制权。

- **UI 侧的配置组合根**：
  app 层并不自己解释具体的 `acquisition`、`driver`、`ui` 配置语义，但它需要最早确保 settings 单例已经就位。后续 UI 设置页会直接基于域命名和 schema 约束生成控件，而不是写一套套单独的 `XxxSettings` 包装类。
  当前约定的典型域路径如下：
  - `acquisition.storage.root_dir`
  - `drivers.<driver_id>.streams.<stream_id>.chunk_size`
  - `drivers.<driver_id>.streams.<stream_id>.nominal_sample_rate_hz`
  - `ui.theme.mode`
  
- **构建硬件组装流水线 (`ModLinkEngine`)**：
  在这里决定了这个“批次”的应用到底挂接带哪些具体的硬件采集能力（比如 `driver = MockDriver()`）。当需要加入 `SerialDriver` 或是 `BluetoothGanglion` 时，直接在此处横向追加塞进 Engine 初始化阶段的 `drivers` 队列；这些实例通常由 app 在调用 `discover_driver_factories()` 后显式构造。
  需要注意：driver 的专用设置不再通过专属 settings dataclass 注入，而是要求 driver 在自己的域下读取 settings。

- **`sys.exit(app.exec())`**:
  将控制权完全并且彻底下放交给 PyQt 的事件循还机制。这也是整套架构**不能脱离或者剥离**掉那些基础 QObject 与 QueuedSignal 连接模型的原因，全场的消息收发（含线程之间切换、绘图重涂）都在被该 `exec()` 背后的死循环隐形的接管派送发报。

## 3. 设计优势与总结

- **清爽的无业务依赖构建**：在程序主入口不夹杂任何具体的读取循环，不用写任何一条线程回收等待指令（因为它们已经在各个底座里利用 `app.aboutToQuit.connect` 自行注册好妥善的释放逻辑）。
- 开发新模块新界面时，在当前层能提供出一种“即插即用”的工作流享受，这是典型的面向对象生命周期交管后的最高体验级结晶。
