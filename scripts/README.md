# ModLink Plugin Scaffold CLI

用于快速创建 ModLink driver plugin 脚手架的交互式命令行工具。

## 功能特性

- 🎨 **美观的交互式界面** - 使用 rich 库提供友好的用户体验
- 📝 **分步向导** - 7 个简单步骤引导你完成配置
- ✅ **自动生成** - 自动创建所有必需的文件和配置
- 🔧 **自动集成** - 自动更新根目录的 pyproject.toml

## 使用方法

运行交互式向导：

```bash
python scripts/cli.py
```

或使用便捷脚本：

**Windows:**
```bash
scripts\create-plugin.bat
```

**Linux/Mac:**
```bash
./scripts/create-plugin.sh
```

## 配置步骤

### Step 1: Basic Information (基本信息)
- **Plugin name**: 插件名称 (如: my-device)
- **Display name**: 显示名称 (如: MyDevice)
- **Device ID**: 设备标识符 (如: my_device)

### Step 2: Driver Type (驱动类型)
- **Driver**: 适合回调/异步风格的驱动
- **LoopDriver**: 适合轮询/定时器风格的驱动

### Step 3: Connection (连接配置)
- **Provider**: 连接提供者 (如: serial, ble, tcp, usb, video)

### Step 4: Stream Configuration (流配置)
- **Modality**: 流模态 (如: eeg, video, audio, accel)
- **Payload type**: 载荷类型
  - `line`: 多通道时间序列数据
  - `plane`: 2D 图像/传感器阵列
  - `video`: RGB 视频流

### Step 5: Data Settings (数据设置)
- **Sample rate**: 采样率 (Hz)
- **Chunk size**: 数据块大小

### Step 6: Channels (通道配置)
- **Channel names**: 通道名称 (逗号分隔，如: ch1,ch2,ch3,ch4)
- **Unit**: 单位 (如: uV, m/s², 留空表示无单位)

### Step 7: Dependencies (依赖)
- **Extra dependencies**: 额外的 Python 包 (逗号分隔)
  - 如: `opencv-python>=4.0, bleak>=0.20`
  - 默认包含: modlink-sdk, numpy>=2.3.3

## 生成的文件结构

```
plugins/my-device/
├── README.md
├── pyproject.toml
└── my_device/
    ├── __init__.py
    ├── driver.py      # 核心驱动实现
    └── factory.py     # 工厂函数
```

## 示例

### 创建 EEG 设备驱动

```
Step 1: my-eeg-device, MyEEGDevice, my_eeg_device
Step 2: LoopDriver
Step 3: serial
Step 4: eeg, line
Step 5: 250 Hz, 25
Step 6: Fp1,Fp2,C3,C4,P3,P4,O1,O2, uV
Step 7: (无额外依赖)
```

### 创建摄像头驱动

```
Step 1: my-camera, MyCamera, my_camera
Step 2: Driver
Step 3: video
Step 4: video, video
Step 5: 30 Hz, 1
Step 6: red,green,blue
Step 7: opencv-python>=4.0
```

### 创建 IMU 驱动

```
Step 1: ble-imu, BleIMU, ble_imu
Step 2: LoopDriver
Step 3: ble
Step 4: imu, line
Step 5: 100 Hz, 10
Step 6: accel_x,accel_y,accel_z,gyro_x,gyro_y,gyro_z
Step 7: bleak>=0.20
```

## 下一步

1. 编辑 `plugins/my-device/my_device/driver.py` 实现设备驱动逻辑
2. 运行 `uv sync --extra my-device` 安装依赖
3. 启动 ModLink Studio 测试驱动

## 提示

- 设备 ID 会自动转换为 snake_case
- 显示名称会自动转换为 PascalCase
- 类名会根据插件名自动生成
- LoopDriver 会自动计算 loop_interval_ms
- 所有配置都会在最后显示摘要供确认
