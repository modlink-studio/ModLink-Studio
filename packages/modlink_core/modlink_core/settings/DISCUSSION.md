# Settings Discussion Notes

这份文件记录当前关于 `modlink_core.settings` 的讨论结论。它是设计草稿，不代表已经落地的实现。

## 当前判断

- 现在的 settings 实现写得不够符合预期，问题不只是代码细节，而是整体建模方式不顺。
- 不应该把 settings 继续做成很重的 backend / service / wrapper 体系。
- 我们真正想要的更像是一个声明式的 settings schema，再配一个很薄的 store。

## 已达成的方向

### 1. UI 设置和后端设置要分开

- 这里说的分开，主要是语义分开，不一定非要分成两套底层存储文件。
- UI 设置属于具体前端。
- 后端设置属于 core / runtime / storage 语义。
- 不能继续做成一个大而全的 `AppSettings` 同时拥有这两类语义。

### 2. 默认不自动落盘

- 设置修改应该先改内存。
- 由上层在合适的时机显式 `save()`。
- 不默认做“每次赋值立即写文件”。

原因：

- UI 场景经常会出现连续编辑。
- 自动落盘会让字段赋值语义和 IO 强耦合。
- 显式保存更符合“settings 是简单对象”的目标。

### 3. 不继续沿着 `SettingsBase` 嵌套对象树硬做

我们讨论过这些写法：

```python
class StorageSettings(SettingsBase):
    path = PathSettings
```

```python
class StorageSettings(SettingsBase):
    path = PathSettings()
```

最后判断是：这条路虽然能做，但实现会越来越像一个对象系统或元编程系统，心智负担偏大，不够直接。

### 4. 更倾向于声明式 schema

当前更认同的方向是：

- 顶层对象描述一个 settings 域
- 用嵌套声明表达结构
- 字段定义里同时放默认值、校验规则、metadata
- 不把 schema 和 metadata 拆成两张平行表

## 当前最认可的设计方向

### 1. 核心概念

建议只保留三类东西：

- `SettingsSpec`
- `group(...)`
- 各种字段定义函数，例如：
  - `bool_setting(...)`
  - `int_setting(...)`
  - `path_setting(...)`
  - `enum_setting(...)`

### 2. 顶层声明方式

我们更认可的风格大致如下：

```python
replay_spec = SettingsSpec(
    namespace="replay",
    schema=group(
        enabled=bool_setting(default=True, scope="project", restart_required=False),
        buffer=group(
            size=int_setting(default=1000, min=1, scope="project", restart_required=True),
        ),
        persist_policy=enum_setting(
            values=["none", "onStop", "always"],
            default="onStop",
            scope="project",
            restart_required=False,
        ),
    ),
)
```

这个方向的优点：

- 比嵌套类更省样板代码
- 可以直接嵌套声明
- 结构更接近最终 JSON
- schema、默认值、校验、metadata 都在一个地方

### 3. 支持嵌套

嵌套不是靠很多类去套，而是靠 `group(...)`：

```python
storage_spec = SettingsSpec(
    namespace="storage",
    schema=group(
        path=group(
            root_dir=path_setting(),
            export_root_dir=path_setting(),
        ),
    ),
)
```

对应 JSON 类似：

```json
{
  "storage": {
    "path": {
      "root_dir": "...",
      "export_root_dir": "..."
    }
  }
}
```

### 4. 默认不要显式传 key

当前讨论结果是：

- 默认用声明里的属性名作为 key
- 先不要设计自定义 key
- 真遇到需要改 key 的场景，再补充能力

也就是说：

- `root_dir=path_setting()` 默认 key 就是 `root_dir`
- `path=group(...)` 默认 key 就是 `path`

## 运行时访问的判断

### 1. 不通过 `spec.schema` 访问值

`schema` 应该只表示定义，不应该同时承担运行时值访问。

不建议这样：

```python
replay_spec.schema.enabled
```

更合理的是分成两层：

- `*_spec` 负责声明
- store 绑定之后得到运行时值视图

例如：

```python
store = SettingsStore(path)
replay = store.bind(replay_spec)

replay.enabled
replay.buffer.size
replay.persist_policy
replay.save()
```

### 2. spec 和 runtime view 分开

这点目前比较明确：

- `SettingsSpec` 是静态声明
- `SettingsStore` 管读写
- `store.bind(spec)` 产出运行时对象

也就是说，不应该把“定义”和“当前值”混成同一个对象。

## 暂时不做的东西

以下能力目前不应该抢先设计：

- 自动落盘
- 事件系统
- 环境变量优先级
- CLI 覆盖
- 兼容层
- 自定义 key
- 很重的 schema registry
- framework 风格的扩展点

## 还没定的点

这些地方后续还需要继续讨论：

- `SettingsStore` 的最小 API 到底长什么样
- 运行时 view 是否允许直接赋值，还是统一通过 `set()`
- `metadata` 里最终保留哪些字段
- scope 是否只保留 `project` / `user`
- 不同 UI 前端的设置是否共用一个 store 文件

## 当前结论一句话版

目前最认同的方向不是“继续打磨一个嵌套 `SettingsBase` 对象系统”，而是：

- 用声明式 `SettingsSpec`
- 用 `group(...)` 表达嵌套
- 用字段定义同时表达默认值、校验和 metadata
- 用一个很薄的 `SettingsStore` 绑定并读写运行时值
