# App 组合根

App 层负责把 SDK、Core、UI 和插件最终组装成一个可运行的应用。

当前最常见的使用方式如下：

```bash
uv sync
uv run --with ./plugins/openbciganglion modlink-studio
```

也就是说，driver 插件默认不进入主 workspace，而是在运行时按需附加。

## App 层负责什么

当前 App 层主要负责：

- 发现可用的 driver entry point
- 创建 `ModLinkEngine`
- 把 driver portal 和 UI 挂到应用入口上
- 启动 Qt 事件循环

## 为什么插件不默认装进主环境

这个项目面对的是多种设备场景，不是所有环境都需要同一个 driver。

所以当前更推荐：

- 根项目只提供平台本体
- 每个具体设备插件放在 `plugins/`
- 需要哪个插件，就在启动时用 `uv run --with ...` 挂进去

这样做的好处是：

- 主环境更干净
- 不需要每加一个 driver 就去改根项目依赖
- 设备开发者可以独立维护自己的插件项目

## 推荐启动方式

### 使用插件

```bash
uv sync
uv run --with ./plugins/openbciganglion modlink-studio
```

### 开发插件

```bash
uv sync
uv run --with-editable ./plugins/openbciganglion modlink-studio
```

`--with-editable` 更适合正在改插件源码的场景，因为本地修改会直接生效。

## App 层和其他层的边界

### 面向设备接入

设备接入通常不需要修改 App 层逻辑，主要需要做的是：

- 写好自己的插件
- 用 `--with` 或 `--with-editable` 附加启动

### 面向应用组装

如果目标是做一个新的展示应用，App 层才是最可能继续扩展的地方。

这里主要决定的是：

- 加载哪些 driver
- 使用哪些 UI 页面
- 默认打开什么布局
- 是否额外组装一些实验场景相关逻辑

## App 层真正提供的价值

App 层的意义不是重复实现设备逻辑，而是：

- 把“哪些设备”“哪些页面”“哪些共享服务”放到一个具体应用里
- 让不同实验或展示场景可以有不同入口

所以它更像“最后一层组装壳”，而不是新一层协议。

## 推荐阅读

- 想接设备：看 [SDK](/sdk)
- 想理解运行时：看 [Core](/core)
- 想做展示页面：看 [UI](/ui)
