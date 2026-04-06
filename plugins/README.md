# 驱动源目录

`plugins/` 保存的是官方驱动源目录，不是最终用户的独立安装入口。

从 `0.2.0` 开始，这些官方驱动代码会内置到 `modlink-studio` 主包里；最终用户通过 `modlink-studio[...]` extras 按需安装第三方依赖。仓库里的这些目录主要用于开发、联调和主包构建。

当前仓库主线是 `0.2.0`。这里的官方驱动也已经按新的纯 Python driver API 迁移，不再以 Qt-style runtime 契约为准。

## 官方驱动

- `host-camera/`
  内置驱动：Host Camera
- `host-microphone/`
  内置驱动：Host Microphone
- `openbci-ganglion/`
  内置驱动：OpenBCI Ganglion

## 仓库内联调

从 monorepo 根目录运行时，官方驱动依赖优先通过根项目 extras 附加：

```bash
uv run --extra official-host-camera modlink-studio
```

```bash
uv run --extra official-host-microphone modlink-studio
```

```bash
uv run --extra official-openbci-ganglion modlink-studio
```
