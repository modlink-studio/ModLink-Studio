# ModLink Shared 模型架构

`modlink_shared` 模块是整个 ModLink-Studio Monorepo 体系中的**最底层数据契约模块**。它没有复杂的业务逻辑，仅仅负责定义系统间流转的“标准化名词”。通过建立强类型数据结构，避免了各模块之间（驱动 ↔ 核心总线 ↔ 后端存储 ↔ UI渲染）因为魔术字典或模糊数据格式而引发的耦合与崩溃。

## 1. 核心边界与生态位

在整个项目中，`modlink_shared` 位于依赖的最末端：
* **无外部依赖**：它除了标准的 Python 库和 `numpy` 之外，**禁止依赖**其他 `modlink` 开头的包。
* **语言中立化倾向**：它虽然写在 Python 中，但它抽象的概念（如帧包、流描述符）在理论上可以直接翻译为 C++ / Rust 的 Struct，用以作为跨界序列化标准。

## 2. 关键代码行为详解

### `models.py` —— 数据“通行货币”

#### 2.1 `PayloadType` (类型别名)
```python
PayloadType: TypeAlias = Literal["line", "plane", "video"]
```
- **行为**：限定了硬件采集上传输的数组形状抽象。
- **作用**：
  - `line`：代表一维独立时间序列的数据，如脑电图（EEG）的波形游走、心电采集的纯时间序列线。
  - `plane`：代表二维矩阵格式更新。
  - `video`：暗示这是一批以帧为基础的三维立方体结构。
- **意图**：指导 UI 层在接到数据时，该用“走纸绘图仪（Line Plot）”还是“图像渲染器（Image View）”来可视化它。

#### 2.2 `StreamDescriptor` (流描述符)
```python
@dataclass(slots=True)
class StreamDescriptor:
    stream_id: str
    modality: str
    payload_type: PayloadType
    nominal_sample_rate_hz: float
    chunk_size: int
    display_name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
```
- **行为**：它是对一条数据传送带的“元信息描述（Schema）”。当一个硬件驱动接入总线前，首先要用此描述符向总线（`StreamBus`）申报：**“我即将发送一种什么样的数据”**。
- **参数解剖**：
  - `stream_id`: **全局唯一**的通道标识符（如 `mock.eeg`, `muse.motion`）。这等同于本数据流的主键。
  - `modality`: 模态种类（如 `eeg`, `emg`, `motion`, `heart_rate`等）。主要用于给采集存储层（如 xdf 等通用标准规范）与后处理系统打标分类。
  - `payload_type`: 对应上文的数据形状说明。
  - `nominal_sample_rate_hz`: 这条流的名义采样率，是 chunk 内时间轴推导的正式字段。
  - `chunk_size`: 这条流单个 `FrameEnvelope` 中承载的时间块长度，是驱动、前端缓存与采集落盘都要共同遵守的正式字段。
  - `metadata`: 存储通道名称列表、单位 (`uV`) 等不需要升格成共享契约正式字段的扩展元信息字典。

#### 2.3 `FrameEnvelope` (核心数据信封)
```python
@dataclass(slots=True)
class FrameEnvelope:
    stream_id: str
    timestamp_ns: int
    data: np.ndarray
    seq: int | None = None
    extra: dict[str, object] = field(default_factory=dict)
```
- **行为**：它是系统中**出现频率最高、流通最广的“活体数据包”**。任何一个驱动从硬件读完了字节、解出了电压值，都必须塞进这个信封，才能封口交给总线。
- **行为特质**：
  - **基于 Numpy 承载**：为了避免原生 list 过度消耗内存并在后续给到科学计算或 UI 高速绘图带来性能瓶颈，数据强制采用 `np.ndarray` 携带。
  - **chunk 起始时钟戳**：`timestamp_ns` 表示这一个 chunk 的起始时间，而不是每个点各自携带独立 timestamp。
  - **数组约定**：第 0 维永远是 channel；对 `line` 类型流，第 1 维永远是 chunk size。也就是说 `line` 数据默认是 `(channel, chunk_size)`。
  - **样本时间轴推导**：chunk 内每个样本的精确时间，不在 `FrameEnvelope` 里逐点携带，而是由 `StreamDescriptor.nominal_sample_rate_hz` 与 `timestamp_ns` 共同推导。

## 3. 设计优势与哲学

1. **防腐化**：在曾经的设计中，底层可能直接借用了 PyQt 宽松的 `signal(object)` 并塞入毫无提示的复杂字典。通过统一 `FrameEnvelope` 的投递，现在如果你的 `StreamBus` 或者 `AcquisitionBackend` 的类型推导生效，任何没有带齐 `timestamp_ns` 的脏数据就会在源头（驱动开发时）被拦截掉。
2. **零拷贝预留**：整个系统从底层往存储和 UI 传递的是带有 `__slots__` 的紧凑型 DataClass （规避 Python 字典内存开销）以及内含 C 语言连续内存块的 `np.ndarray` 引用对象的指针流交接。当 `StreamBus` 用信号（Signal）广播分发时，它本身不会导致高频大数据块产生昂贵的深拷贝。
