# 插件源目录

`plugins/` 保存的是官方插件源目录，不是最终用户的安装入口。

第一版正式分发时，官方插件会以独立 Python 包的形式发布到 Cloudsmith 仓库 `xylt-space/modlink-studio`。最终用户通过 `modlink-studio[...]` extras 安装插件；仓库里的这些目录主要用于开发、联调和发布构建。

## 官方插件

- `host-camera/`
  对外分发名：`modlink-plugin-host-camera`
- `host-microphone/`
  对外分发名：`modlink-plugin-host-microphone`
- `openbci-ganglion/`
  对外分发名：`modlink-plugin-openbci-ganglion`

## 仓库内联调

从 monorepo 根目录运行时，官方插件优先通过根项目 extras 附加：

```bash
uv run --extra official-host-camera modlink-studio
```

```bash
uv run --extra official-host-microphone modlink-studio
```

```bash
uv run --extra official-openbci-ganglion modlink-studio
```
