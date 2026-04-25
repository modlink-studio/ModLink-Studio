# @modlink-studio/plugin-scaffold

`@modlink-studio/plugin-scaffold` 是独立发布的 React + Ink CLI，用来生成 ModLink Python driver 项目模板。

## Usage

公开使用：

```bash
npx @modlink-studio/plugin-scaffold --zh
```

Headless / AI agent / CI 使用：

```bash
npx @modlink-studio/plugin-scaffold schema --json
npx @modlink-studio/plugin-scaffold validate --stdin --json < plugin.spec.json
npx @modlink-studio/plugin-scaffold generate --stdin --json --out ./plugins < plugin.spec.json
```

仓库内开发：

```bash
npm install
npm --workspace @modlink-studio/plugin-scaffold run dev -- --zh
npm --workspace @modlink-studio/plugin-scaffold run dev -- schema --json
```

全局安装后也可以直接运行：

```bash
npm install -g @modlink-studio/plugin-scaffold
modlink-plugin-scaffold --zh
```

## What It Generates

- `pyproject.toml`
- `README.md`
- `LICENSE`
- `.gitignore`
- `<plugin_name>/__init__.py`
- `<plugin_name>/driver.py`
- `<plugin_name>/factory.py`
- `tests/test_smoke.py`

生成目标仍然是独立的 Python driver 包，面向 `modlink-sdk` 与 `modlink.drivers` entry point 契约。

## Headless Input

`generate` 和 `validate` 从 stdin 读取 JSON。典型输入如下：

```json
{
  "pluginName": "serial-pressure",
  "displayName": "Serial Pressure",
  "deviceId": "serial_pressure.01",
  "providers": ["serial"],
  "dataArrival": "poll",
  "driverKind": "loop",
  "dependencies": ["pyserial>=3.5"],
  "streams": [
    {
      "streamKey": "pressure",
      "displayName": "Pressure",
      "payloadType": "signal",
      "sampleRateHz": 100,
      "chunkSize": 10,
      "channelNames": ["left", "right"],
      "unit": "kPa"
    }
  ]
}
```

这些 headless 命令只负责确定性校验和生成，不调用 AI。AI 插件生成由 Python CLI `modlink-plugin-agent` 编排：它先调用本工具生成骨架，再补全 driver 代码并运行验证。

## Development Tooling

这个工具目录单独使用 `Biome` 管理 TypeScript / React + Ink 的格式化和基础 lint。

常用命令：

```bash
npm --workspace @modlink-studio/plugin-scaffold run lint
npm --workspace @modlink-studio/plugin-scaffold run lint:fix
npm --workspace @modlink-studio/plugin-scaffold run format
```

如果你已经在 monorepo 根目录，也可以直接使用根脚本：

```bash
npm run scaffold:lint
npm run scaffold:lint:fix
npm run scaffold:format
```

提交前检查会通过根目录的 `pre-commit` 配置自动调用这条工具链，因此 `tools/modlink_plugin_scaffold/` 下的改动会同时经过：

- `Biome` 的格式化与基础 lint
- 尾空格清理
- 文件末尾换行修复

当前 `Biome` 配置文件位于 [biome.json](biome.json)。
