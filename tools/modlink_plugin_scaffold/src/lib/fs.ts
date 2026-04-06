import fs from "node:fs/promises";
import path from "node:path";

import {
  renderDriverPy,
  renderFactoryPy,
  renderGitIgnore,
  renderInitPy,
  renderLicense,
  renderPyprojectToml,
  renderReadme,
  renderSmokeTest,
} from "../templates/render.js";
import type { DriverSpec, GeneratedProject, Language } from "./types.js";

export class ScaffoldExistsError extends Error {
  readonly projectDir: string;

  constructor(projectDir: string) {
    super(`Target directory already exists: ${projectDir}`);
    this.name = "ScaffoldExistsError";
    this.projectDir = projectDir;
  }
}

export function getGeneratedProject(spec: DriverSpec, cwd: string): GeneratedProject {
  const projectDir = path.join(cwd, spec.pluginName);
  return {
    projectDir,
    writtenFiles: [
      path.join(projectDir, "pyproject.toml"),
      path.join(projectDir, "README.md"),
      path.join(projectDir, "LICENSE"),
      path.join(projectDir, ".gitignore"),
      path.join(projectDir, spec.pluginName, "__init__.py"),
      path.join(projectDir, spec.pluginName, "driver.py"),
      path.join(projectDir, spec.pluginName, "factory.py"),
      path.join(projectDir, "tests", "test_smoke.py"),
    ],
    commands: {
      install: "python -m pip install -e .",
      test: "python -m pytest",
      runHost: "python -m modlink_studio",
      checkEntryPoints:
        "python -c \"from importlib.metadata import entry_points; print(sorted(ep.name for ep in entry_points(group='modlink.drivers')))\"",
    },
  };
}

export async function writeProjectFiles(
  spec: DriverSpec,
  cwd: string,
  language: Language,
  overwrite: boolean,
): Promise<GeneratedProject> {
  const generated = getGeneratedProject(spec, cwd);
  const exists = await fs
    .access(generated.projectDir)
    .then(() => true)
    .catch(() => false);

  if (exists && !overwrite) {
    throw new ScaffoldExistsError(generated.projectDir);
  }

  if (exists) {
    await fs.rm(generated.projectDir, { recursive: true, force: true });
  }

  const packageDir = path.join(generated.projectDir, spec.pluginName);
  const testsDir = path.join(generated.projectDir, "tests");
  await fs.mkdir(packageDir, { recursive: true });
  await fs.mkdir(testsDir, { recursive: true });

  const fileMap = new Map<string, string>([
    [path.join(generated.projectDir, "pyproject.toml"), renderPyprojectToml(spec)],
    [path.join(generated.projectDir, "README.md"), renderReadme(spec, language)],
    [path.join(generated.projectDir, "LICENSE"), renderLicense()],
    [path.join(generated.projectDir, ".gitignore"), renderGitIgnore()],
    [path.join(packageDir, "__init__.py"), renderInitPy(spec)],
    [path.join(packageDir, "driver.py"), renderDriverPy(spec)],
    [path.join(packageDir, "factory.py"), renderFactoryPy(spec)],
    [path.join(testsDir, "test_smoke.py"), renderSmokeTest(spec)],
  ]);

  await Promise.all(
    Array.from(fileMap.entries()).map(async ([filePath, content]) => {
      await fs.writeFile(filePath, content, "utf8");
    }),
  );

  return generated;
}
