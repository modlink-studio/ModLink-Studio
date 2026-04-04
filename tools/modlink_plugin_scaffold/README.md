# @modlink-studio/plugin-scaffold

`@modlink-studio/plugin-scaffold` 是独立发布的 React + Ink CLI，用来生成 ModLink Python driver 项目模板。

## Usage

公开使用：

```bash
npx @modlink-studio/plugin-scaffold --zh
```

仓库内开发：

```bash
npm install
npm --workspace @modlink-studio/plugin-scaffold run dev -- --zh
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
