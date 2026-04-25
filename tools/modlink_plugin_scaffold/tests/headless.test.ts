import { spawnSync } from "node:child_process";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { afterEach, describe, expect, test } from "vitest";

const packageRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const cliPath = path.join(packageRoot, "src", "cli.tsx");
const tempDirs: string[] = [];

async function makeTempDir(): Promise<string> {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), "modlink-plugin-headless-"));
  tempDirs.push(dir);
  return dir;
}

function runCli(args: string[], input?: object) {
  return spawnSync(process.execPath, ["--import", "tsx", cliPath, ...args], {
    cwd: packageRoot,
    encoding: "utf8",
    input: input === undefined ? undefined : JSON.stringify(input),
  });
}

function validInput() {
  return {
    pluginName: "ai-device",
    displayName: "AI Device",
    deviceId: "ai_device.01",
    providers: ["serial"],
    dataArrival: "poll",
    driverKind: "loop",
    dependencies: ["pyserial>=3.5"],
    streams: [
      {
        streamKey: "pressure",
        displayName: "Pressure",
        payloadType: "signal",
        sampleRateHz: 100,
        chunkSize: 10,
        channelNames: ["left", "right"],
        unit: "kPa",
      },
    ],
  };
}

afterEach(async () => {
  await Promise.all(
    tempDirs.splice(0).map(async (dir) => fs.rm(dir, { recursive: true, force: true })),
  );
});

describe("headless CLI", () => {
  test("prints the scaffold schema without requiring a TTY", () => {
    const result = runCli(["schema", "--json"]);

    expect(result.status).toBe(0);
    const payload = JSON.parse(result.stdout);
    expect(payload.ok).toBe(true);
    expect(payload.schema.properties.streams.items.properties.payloadType.enum).toContain("signal");
  });

  test("validates scaffold JSON from stdin", () => {
    const result = runCli(["validate", "--stdin", "--json"], {
      pluginName: "",
      providers: [],
      streams: [],
    });

    expect(result.status).toBe(1);
    const payload = JSON.parse(result.stdout);
    expect(payload.ok).toBe(false);
    expect(payload.errors.pluginName).toBeTruthy();
  });

  test("generates a project from JSON stdin", async () => {
    const outDir = await makeTempDir();
    const result = runCli(["generate", "--stdin", "--json", "--out", outDir], validInput());

    expect(result.status).toBe(0);
    const payload = JSON.parse(result.stdout);
    expect(payload.ok).toBe(true);
    expect(payload.projectDir).toBe(path.join(outDir, "ai_device"));
    await expect(
      fs.readFile(path.join(outDir, "ai_device", "pyproject.toml"), "utf8"),
    ).resolves.toContain("pyserial>=3.5");
  });

  test("keeps interactive mode unavailable in non-TTY shells", () => {
    const result = runCli([]);

    expect(result.status).toBe(1);
    expect(result.stderr).toContain("interactive mode requires a TTY");
  });
});
