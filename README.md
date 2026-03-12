<p align="center">
  <img src="src/openbciganglionui/assets/app_icon.png" alt="OpenBCI Ganglion UI icon" width="96" />
</p>

<h1 align="center">OpenBCI Ganglion UI</h1>

<p align="center">
  这是一个基于 <code>PyQt6</code> 和 <code>PyQt6-Fluent-Widgets</code> 的桌面采集界面项目，使用 <code>uv</code> 管理依赖与环境。
</p>

![OpenBCI Ganglion UI screenshot](docs/images/ui-demo.png)

## 安装 uv

### 官方安装脚本

Windows：

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

macOS 和 Linux：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 使用 pipx 安装

如果你已经安装了 `pipx`，也可以直接安装 `uv`：

```bash
pipx install uv
```

参考官方文档：
- `uv` 安装文档：https://docs.astral.sh/uv/getting-started/installation/

## 快速开始

安装项目依赖并启动：

```bash
uv sync
uv run openbciganglionui
```

也可以用模块方式启动：

```bash
uv run python -m openbciganglionui
```

默认会启动 BrainFlow backend。

## 项目结构

```text
src/openbciganglionui/
  app.py          # QApplication 启动入口
  backend/        # backend 协议、事件模型和 BrainFlow 实现
  ui/             # 页面、窗口、设置管理和组件
  __main__.py     # python -m 入口
```

## 开发

安装开发依赖：

```bash
uv sync --dev
```

运行检查：

```bash
uv run ruff check .
```

手工 backend 冒烟测试：

```powershell
uv run openbciganglionui-backend-smoke --method native --search
```

如果走 dongle，可以显式指定串口：

```powershell
uv run openbciganglionui-backend-smoke --method dongle --serial-port COM3
```

如果要绕过 UI 和 backend 封装，只直接验证 BrainFlow Native BLE 链路：

```powershell
uv run openbciganglionui-brainflow-native-probe --firmware-hints auto
```

如果已经知道设备名，也可以显式传给 `serial_number`：

```powershell
uv run openbciganglionui-brainflow-native-probe --serial-number Ganglion-9c3b --firmware-hints auto
```

### Native BLE 经验记录

在 Windows 11 + BrainFlow 5.21.0 + Ganglion Native BLE 的实测里，目前观察到：

- `autodiscover + fw:auto` 可以成功连接，且 BrainFlow 会自动识别为固件 `2`
- 显式指定 `fw:2` 和 `fw:3` 也都可以成功连接
- `serial_number=设备名` 这条路径也可以成功连接，例如 `Ganglion-9c3b`
- 显式传 `mac_address` 时，即使 MAC 本身是对的，也无法成功连接，表现为 `Failed to find Ganglion Device` / `BOARD_NOT_READY_ERROR:7`
- 同时传 `mac_address + serial_number` 时，结果仍然和显式 MAC 一样失败

因此当前项目里的 Native BLE 策略是：

- 搜索结果里仍然显示 MAC 地址，便于用户识别设备
- 真正连接时优先使用显式 `serial_number`
- 不把扫描得到的 `mac_address` 作为 Native BLE 的连接参数

这部分是经验性结论，不是 BrainFlow 官方保证；如果后续升级 BrainFlow 或更换系统蓝牙栈，需要重新验证。

## 打包发布

当前仓库已经提供了 Windows 桌面应用的 `PyInstaller` 打包配置：

- 入口脚本：[packaging/app_entry.py](packaging/app_entry.py)
- 规格文件：[packaging/app.spec](packaging/app.spec)
- 构建脚本：[scripts/build_app.ps1](scripts/build_app.ps1)

在项目根目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_app.ps1
```

构建完成后，产物位于：

```text
release/OpenBCIGanglionUI/OpenBCIGanglionUI.exe
```

补充说明：

- 当前使用 `PyInstaller onedir` 方式打包，运行时需要保留同目录下的 `_internal` 文件夹。
- 构建日志中可能出现 `qframelesswindow.webengine` 与 `PyQt6.QtWebEngineWidgets` 相关提示；当前发布版本不依赖该组件，不影响应用打包和运行。
- 构建日志中可能出现 `QFluentWidgets Pro` 的宣传提示；这是构建阶段输出，不会出现在打包后应用的启动界面中。

## 平台说明

- 源码运行主要依赖 `PyQt6`、`numpy` 和 `PyQt6-Fluent-Widgets`，代码本身没有明显写死 Windows 运行逻辑。
- 因此，源码方式在 Linux 上预计也是可以运行的，`uv sync` 正常情况下也不应有问题。
- 但目前我只实际验证了 Windows 环境，Linux 还没有做过完整运行测试。
