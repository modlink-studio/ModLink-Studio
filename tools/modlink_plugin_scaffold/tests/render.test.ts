import { describe, expect, test } from "vitest";

import { scaffoldRenderOptions } from "../src/render-app.js";

describe("renderScaffoldApp", () => {
  test("uses bounded incremental terminal rendering", () => {
    expect(scaffoldRenderOptions.patchConsole).toBe(true);
    expect(scaffoldRenderOptions.incrementalRendering).toBe(true);
    expect(scaffoldRenderOptions.maxFps).toBe(60);
  });
});
