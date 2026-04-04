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

  test("updates the derived preview after editing the plugin name", async () => {
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
    app.stdin.write("\r");
    await flush();

    expect(app.lastFrame()).toContain("demo-device");
    expect(app.lastFrame()).toContain("DemoDevice");
    expect(app.lastFrame()).toContain("demo_device.01");
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

  test("switches preview tabs and supports stream actions", async () => {
    const cwd = await makeTempDir();
    const app = render(<ScaffoldApp language="en" cwd={cwd} />);
    await flush();

    app.stdin.write("]");
    await flush();
    expect(app.lastFrame()).toContain("class MyDeviceDriver");

    app.stdin.write("\t");
    app.stdin.write("\t");
    app.stdin.write("\t");
    await flush();
    pressArrow(app.stdin, "down");
    await flush();
    app.stdin.write("\r");
    await flush();

    expect(app.lastFrame()).toContain("2. Stream 2");
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
