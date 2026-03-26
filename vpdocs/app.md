# App 组合根

App 层是 ModLink Studio 的最终桌面宿主入口。  
它的职责不是重新定义 SDK 契约，也不是接管 Core 的运行时细节，而是把已经存在的几层能力装配成一个真正可启动的应用。

如果概括成一句话，可以理解为：

- SDK 定义 driver 契约
- Core 托管 driver、流和录制相关运行时
- UI 提供页面和窗口
- App 负责把这些东西组装成最终程序

## 这页主要回答什么

这页主要回答四个问题：

1. 最终用户从哪里启动宿主
2. App 层启动时到底会创建哪些对象
3. 已安装的 driver 是怎么被发现的
4. App 层保留了哪些 fail-fast 边界

## 启动入口

正式安装方式见 [安装与发布](/install)。安装完成后，App 层提供两个入口：

正式用户入口：

```bash
modlink-studio
```

调试入口：

```bash
python -m modlink_studio
```

这两个入口最终都会走到同一个启动逻辑，本质上都会调用同一套 `main()`。  
对实际使用来说，这里最重要的区别只有一件事：是否带控制台输出。

- `modlink-studio` 作为 GUI 入口，日常使用时通常不会额外带一个控制台窗口
- `python -m modlink_studio` 是从终端直接启动，标准输出和报错都会留在当前控制台里

因此当前建议是：

- 日常启动宿主：`modlink-studio`
- 联调 driver、看日志和排查报错：`python -m modlink_studio`

## App 层到底负责什么

App 层是组合根。它对系统做的事情很具体：

1. 创建或复用 `QApplication`
2. 设置应用名、图标和主题
3. 初始化设置服务
4. 发现当前环境里的 driver factories
5. 创建 `ModLinkEngine`
6. 创建主窗口 `MainWindow`
7. 启动 Qt 事件循环

这层的核心特征是“装配”，而不是“定义新协议”。  
也就是说，App 层负责把现成的 SDK、Core、UI 和插件接起来，而不是在这里定义设备协议、流模型或录制格式。

## 一个启动流程大概长什么样

从当前实现看，宿主启动顺序大致是：

1. 创建 `QApplication`
2. 加载应用图标和主题
3. 创建 `SettingsService`
4. 扫描 `modlink.drivers`
5. 用扫描到的 driver factories 创建 `ModLinkEngine`
6. 用这个 engine 创建 `MainWindow`
7. `show()` 窗口并进入 Qt 事件循环

这条顺序有助于理解 App 层和其他层之间的关系：

- driver 发现发生在应用启动阶段
- Core 运行时在窗口创建前就已经准备好
- UI 页面拿到的是已经组装好的 engine，而不是自己去拼 driver 或流总线

## 插件发现模型

宿主不会在运行时临时下载插件，也不会要求最终用户拼接本地路径。当前模型是“先安装，再发现”：

- 官方插件通过 `modlink-studio[...]` extras 安装
- 外部 driver 用普通 `pip install` 或 `pip install -e` 安装到同一个 Python 环境
- 宿主启动时扫描当前环境里的 `modlink.drivers`

例如一个外部 driver 的典型联调方式是：

```bash
python -m pip install -e ../my_driver
python -m modlink_studio
```

这个模型意味着两件事：

- App 层只负责发现已经安装好的 driver
- driver 的安装和版本管理发生在 Python 包环境层，而不是宿主界面层

## 为什么外部 driver 不依赖宿主应用

`modlink-studio` 是最终桌面宿主，不是 driver 的最小公共接口。

外部 driver 更合理的依赖边界是：

- 默认依赖 `modlink-sdk`
- 只有确实需要运行时服务时，才额外依赖 `modlink-core`

这样做的原因不是“形式上分层”，而是为了让 driver 依赖最小稳定接口，而不是反向绑死在整个宿主应用上。  
App 层只负责在启动时把这些已安装 driver 发现出来，并把它们交给 Core 和 UI 使用。

## App 层保留的 fail-fast 边界

App 层当前明确保留 fail-fast 策略。

这意味着：

- 损坏的 driver entry point 会在启动或加载阶段直接暴露错误
- 未知 payload 类型不会在 App 层被静默吞掉
- 明显的插件协议错误应尽早暴露，而不是拖到运行过程中变成更难排查的问题

这里的判断很明确：driver 是系统核心组成，不是可有可无的附属插件。  
如果 driver 协议本身有问题，让宿主尽早失败，通常比启动一个语义不清的应用更合理。

## 仓库内联调

`plugins/` 目录里保留的是官方插件源目录和开发态示例插件。  
在 monorepo 根目录联调时，可以通过根项目 extras 启动宿主：

```bash
uv run --extra official-host-camera modlink-studio
```

```bash
uv run --extra official-openbci-ganglion modlink-studio
```

如果目的是理解 driver 契约，优先继续看 [SDK](/sdk)。  
如果目的是理解 runtime 如何托管 driver 和流，继续看 [Core](/core)。
