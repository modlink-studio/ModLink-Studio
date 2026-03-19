# ModLink Bus

这份文档只描述当前 `StreamBus` 的职责、接口和使用方式。

对应实现文件：

- `packages/modlink_core/bus/stream_bus.py`（monorepo 内的真实实现）
- `src/modlink/bus/stream_bus.py`（对外 facade）

## 目标

- 总线只负责注册流和广播帧
- 设备模块不需要依赖总线类本身
- 每个 stream 在注册时都绑定一个 `FrameEnvelope` signal
- 其他模块统一订阅全部帧
- 当前不支持“只订阅单个 stream”

## 核心类

### `StreamBus`

`StreamBus` 是总线本体，负责：

- 注册 `StreamDescriptor`
- 为每个流绑定一个输入 signal
- 保存已经注册的 descriptor
- 广播所有合法的 `FrameEnvelope`
- 在出错时发出字符串类型的 `sig_error`

主要信号：

- `sig_frame`
- `sig_error`

主要方法：

- `register_stream(descriptor: StreamDescriptor, frame_signal: FrameSignal) -> None`
- `publish_frame(frame: object) -> None`
- `subscribe(sink: Callable[[FrameEnvelope], None]) -> FrameSubscription`
- `descriptor(stream_id: str) -> StreamDescriptor | None`
- `descriptors() -> dict[str, StreamDescriptor]`

### `FrameSubscription`

`FrameSubscription` 是订阅句柄。

主要职责：

- 表示一次订阅关系
- 提供退订能力

主要属性：

- `active`

主要方法：

- `close() -> None`
- `unsubscribe() -> None`

## 调用流程

### 1. 注册流

```python
from PyQt6.QtCore import QObject, pyqtSignal

from modlink import StreamBus, StreamDescriptor


class Driver(QObject):
    sig_eeg_frame = pyqtSignal(object)

bus = StreamBus()
driver = Driver()

bus.register_stream(
    StreamDescriptor(
        stream_id="eeg.main",
        modality="eeg",
        payload_type="list[float]",
        display_name="Main EEG",
    ),
    driver.sig_eeg_frame,
)
```

这一步完成后：

- bus 记住这个 descriptor
- bus 把这个 signal 接到自己的接收槽上
- 后续 driver 只需要正常 emit 自己的 signal

### 2. 发布帧

```python
from modlink import FrameEnvelope

driver.sig_eeg_frame.emit(
    FrameEnvelope(
        stream_id="eeg.main",
        timestamp_ns=123456789,
        payload=[1.0, 2.0, 3.0, 4.0],
        seq=1,
    )
)
```

### 3. 订阅数据

```python
def on_frame(frame):
    print(frame.stream_id, frame.payload)


subscription = bus.subscribe(on_frame)
```

也可以传入可调用对象：

```python
class PlotSink:
    def __call__(self, frame):
        print(frame.seq)


subscription = bus.subscribe(PlotSink())
```

### 4. 退订

```python
subscription.close()
```

或者：

```python
subscription.unsubscribe()
```

## 错误行为

当前错误信号统一使用 `str`，还没有上正式错误模型。

### 重复注册冲突 descriptor

如果同一个 `stream_id` 被再次注册，且 descriptor 内容不同：

- `StreamBus.sig_error` 发出字符串错误
- `register_stream()` 抛出 `ValueError`

### 发布未注册流

如果直接发布一个未注册流的帧：

- `StreamBus.sig_error` 发出字符串错误
- 该帧不会继续广播

### 发送的对象不是 `FrameEnvelope`

如果注册进来的 signal 发出的不是 `FrameEnvelope`：

- `StreamBus.sig_error` 发出字符串错误
- 该对象不会继续广播

## 当前边界

`StreamBus` 当前不负责这些事情：

- 不负责设备连接逻辑
- 不负责录制逻辑
- 不负责 marker / segment
- 不负责 UI 展示
- 不负责按单个 `stream_id` 订阅

## 设计约束

- 设备模块不需要知道 `StreamBus` 内部实现
- 设备模块只需要暴露每个 stream 对应的 signal
- 消费者模块只需要订阅帧，不需要在总线层声明自己关心哪个 stream
- bus 内部保存 descriptor，但对外只返回拷贝，不暴露内部字典本体
