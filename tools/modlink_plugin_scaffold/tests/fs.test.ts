import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";

import { afterEach, describe, expect, test } from "vitest";

import { getGeneratedProject, ScaffoldExistsError, writeProjectFiles } from "../src/lib/fs.js";
import { createDefaultDraft, validateDraft } from "../src/lib/spec.js";

const tempDirs: string[] = [];

async function makeTempDir(): Promise<string> {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), "modlink-plugin-scaffold-"));
  tempDirs.push(dir);
  return dir;
}

afterEach(async () => {
  await Promise.all(
    tempDirs.splice(0).map(async (dir) => fs.rm(dir, { recursive: true, force: true })),
  );
});

describe("file generation", () => {
  test("writes the generated project tree", async () => {
    const cwd = await makeTempDir();
    const spec = validateDraft("en", createDefaultDraft()).spec;
    expect(spec).not.toBeNull();
    if (!spec) {
      throw new Error("expected valid spec");
    }

    const generated = await writeProjectFiles(spec, cwd, "en", false);

    expect(generated.projectDir).toBe(path.join(cwd, "my_device"));
    await expect(
      fs.readFile(path.join(generated.projectDir, "LICENSE"), "utf8"),
    ).resolves.toContain("MIT License");
    await expect(
      fs.readFile(path.join(generated.projectDir, "tests", "test_smoke.py"), "utf8"),
    ).resolves.toContain("create_driver");
  });

  test("throws when the target already exists unless overwrite is enabled", async () => {
    const cwd = await makeTempDir();
    const spec = validateDraft("en", createDefaultDraft()).spec;
    expect(spec).not.toBeNull();
    if (!spec) {
      throw new Error("expected valid spec");
    }
    const existing = getGeneratedProject(spec, cwd).projectDir;

    await fs.mkdir(existing, { recursive: true });
    await expect(writeProjectFiles(spec, cwd, "en", false)).rejects.toBeInstanceOf(
      ScaffoldExistsError,
    );
    await expect(writeProjectFiles(spec, cwd, "en", true)).resolves.toMatchObject({
      projectDir: existing,
    });
  });
});
