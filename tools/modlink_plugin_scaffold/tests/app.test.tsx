import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";

import React from "react";
import {cleanup, render} from "ink-testing-library";
import {afterEach, describe, expect, test} from "vitest";

import {ScaffoldApp} from "../src/app.js";
import {createDefaultDraft} from "../src/lib/spec.js";

const tempDirs: string[] = [];

async function makeTempDir(): Promise<string> {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), "modlink-plugin-ink-"));
  tempDirs.push(dir);
  return dir;
}

async function flush(): Promise<void> {
  await new Promise((resolve) => setTimeout(resolve, 20));
}

function pressArrow(stdin: {write: (data: string) => void}, direction: "up" | "down" | "left" | "right"): void {
  const map = {
    up: "\u001B[A",
    down: "\u001B[B",
    right: "\u001B[C",
    left: "\u001B[D",
  } as const;
  stdin.write(map[direction]);
}

function pressBackspace(stdin: {write: (data: string) => void}, count: number): void {
  for (let index = 0; index < count; index += 1) {
    stdin.write("\u007F");
  }
}

afterEach(async () => {
  cleanup();
  await Promise.all(tempDirs.splice(0).map(async (dir) => fs.rm(dir, {recursive: true, force: true})));
});

describe("ScaffoldApp", () => {
  test("renders in English and Chinese", async () => {
    const cwd = await makeTempDir();
    const enApp = render(<ScaffoldApp language="en" cwd={cwd} />);
    await flush();
    expect(enApp.lastFrame()).toContain("ModLink Plugin Scaffold");
    enApp.unmount();

    const zhApp = render(<ScaffoldApp language="zh" cwd={cwd} />);
    await flush();
    expect(zhApp.lastFrame()).toContain("ModLink 插件脚手架");
  });

  test("keeps the banner stable until enter commits the edit", async () => {
    const cwd = await makeTempDir();
    const draft = createDefaultDraft();
    draft.pluginName = "";
    draft.displayName = "";
    draft.deviceId = "";

    const app = render(<ScaffoldApp language="en" cwd={cwd} initialDraft={draft} />);
    await flush();

    app.stdin.write("\r");
    await flush();
    app.stdin.write("demo-device");
    await flush();

    expect(app.lastFrame()).toContain("demo-device");
    expect(app.lastFrame()).toContain("Validation errors");

    app.stdin.write("\r");
    await flush();

    expect(app.lastFrame()).toContain("demo-device");
    expect(app.lastFrame()).toContain("DemoDevice");
    expect(app.lastFrame()).toContain("demo_device.01");
  });

  test("supports escape to cancel an in-progress edit", async () => {
    const cwd = await makeTempDir();
    const app = render(<ScaffoldApp language="en" cwd={cwd} />);
    await flush();

    app.stdin.write("\r");
    await flush();
    pressBackspace(app.stdin, 9);
    app.stdin.write("cancelled");
    await flush();
    app.stdin.write("\u001B");
    await flush();

    expect(app.lastFrame()).toContain("my-device");
    expect(app.lastFrame()).not.toContain("cancelled█");
  });

  test("accepts unicode text input on commit", async () => {
    const cwd = await makeTempDir();
    const app = render(<ScaffoldApp language="zh" cwd={cwd} />);
    await flush();

    pressArrow(app.stdin, "down");
    await flush();
    app.stdin.write("\r");
    await flush();
    app.stdin.write("测试设备");
    await flush();
    app.stdin.write("\r");
    await flush();

    expect(app.lastFrame()).toContain("测试设备");
  });

  test("updates driver recommendation when data arrival changes", async () => {
    const cwd = await makeTempDir();
    const app = render(<ScaffoldApp language="en" cwd={cwd} />);
    await flush();

    app.stdin.write("\t");
    await flush();
    pressArrow(app.stdin, "down");
    await flush();
    pressArrow(app.stdin, "left");
    await flush();
    app.stdin.write("\t");
    await flush();

    expect(app.lastFrame()).toContain("Recommended: LoopDriver");
  });

  test("supports stream actions in the single-column layout", async () => {
    const cwd = await makeTempDir();
    const app = render(<ScaffoldApp language="en" cwd={cwd} />);
    await flush();

    expect(app.lastFrame()).toContain("my-device");
    expect(app.lastFrame()).not.toContain("driver.py");

    app.stdin.write("\t");
    app.stdin.write("\t");
    app.stdin.write("\t");
    await flush();
    expect(app.lastFrame()).toContain("[Streams]");
    expect(app.lastFrame()).toContain("[Current stream details]");
    expect(app.lastFrame()).toContain("[Controls]");
    expect(app.lastFrame()).toContain("Add stream");
    expect(app.lastFrame()).toContain("Delete stream");
    expect(app.lastFrame()).not.toContain("Duplicate stream");
    expect(app.lastFrame()).not.toContain("Move stream up");
    expect(app.lastFrame()).not.toContain("<>");
    pressArrow(app.stdin, "down");
    await flush();
    app.stdin.write("\r");
    await flush();

    expect(app.lastFrame()).toContain("Stream 2");
  });

  test("renders global section tabs and the top banner", async () => {
    const cwd = await makeTempDir();
    const app = render(<ScaffoldApp language="zh" cwd={cwd} />);
    await flush();

    expect(app.lastFrame()).toContain("[基本信息]");
    expect(app.lastFrame()).toContain("连接方式");
    expect(app.lastFrame()).toContain("Driver 类型");
    expect(app.lastFrame()).toContain("Streams");
    expect(app.lastFrame()).toContain("依赖");
    expect(app.lastFrame()).toContain("定义生成项目的包名");
    expect(app.lastFrame()).toContain("脚手架摘要");
    expect(app.lastFrame()).toContain("my-device");
    expect(app.lastFrame()).toContain("Device ID");
    expect(app.lastFrame()).not.toContain("driver.py");
    expect(app.lastFrame()).toContain("位置:");
    expect(app.lastFrame()).toContain("操作:");
  });

  test("blocks generation for invalid drafts", async () => {
    const cwd = await makeTempDir();
    const draft = createDefaultDraft();
    draft.pluginName = "";

    const app = render(<ScaffoldApp language="en" cwd={cwd} initialDraft={draft} />);
    await flush();
    app.stdin.write("g");
    await flush();

    expect(app.lastFrame()).toContain("Plugin name must contain at least one letter");
  });

  test("confirms overwrite and generates files", async () => {
    const cwd = await makeTempDir();
    await fs.mkdir(path.join(cwd, "my_device"), {recursive: true});
    const app = render(<ScaffoldApp language="en" cwd={cwd} />);
    await flush();

    app.stdin.write("g");
    await flush();
    expect(app.lastFrame()).toContain("Overwrite existing project?");

    pressArrow(app.stdin, "right");
    await flush();
    app.stdin.write("\r");
    await flush();

    expect(app.lastFrame()).toContain("Scaffold generated");
    await expect(fs.readFile(path.join(cwd, "my_device", "pyproject.toml"), "utf8")).resolves.toContain('license = "MIT"');
  });
});
