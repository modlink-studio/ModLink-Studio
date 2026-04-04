import path from "node:path";

import {describe, expect, test} from "vitest";

import {buildPreviewBundle, renderLicense, renderPyprojectToml, renderReadme} from "../src/templates/render.js";
import {applyPayloadDefaults, createDefaultDraft, makeDeviceId, sanitizeIdentifier, toPascalCase, validateDraft} from "../src/lib/spec.js";

describe("spec helpers", () => {
  test("normalizes plugin identity and derives defaults", () => {
    expect(sanitizeIdentifier("My Device")).toBe("my_device");
    expect(toPascalCase("my_device")).toBe("MyDevice");
    expect(makeDeviceId("My Device")).toBe("my_device.01");
  });

  test("replaces stream defaults when payload type changes", () => {
    const draft = createDefaultDraft();
    const video = applyPayloadDefaults(draft.streams[0], "video");

    expect(video.payloadType).toBe("video");
    expect(video.channelNames).toBe("red, green, blue");
    expect(video.videoHeight).toBe("480");
    expect(video.videoWidth).toBe("640");
  });

  test("validates a complete draft into a driver spec", () => {
    const validation = validateDraft("en", createDefaultDraft());

    expect(validation.fieldErrors).toEqual({});
    expect(validation.spec?.pluginName).toBe("my_device");
    expect(validation.spec?.driverKind).toBe("driver");
    expect(validation.spec?.streams[0]?.channelNames).toEqual(["ch1", "ch2"]);
    expect(validation.recommendedDriverKind).toBe("driver");
  });

  test("surfaces validation errors for invalid drafts", () => {
    const invalid = createDefaultDraft();
    invalid.pluginName = "";
    invalid.providersText = "";
    invalid.streams[0].channelNames = "";

    const validation = validateDraft("zh", invalid);

    expect(validation.spec).toBeNull();
    expect(Object.keys(validation.fieldErrors)).toEqual(expect.arrayContaining(["pluginName", "providersText", "streams.0.channelNames"]));
  });
});

describe("template rendering", () => {
  test("builds previews for a valid spec", () => {
    const spec = validateDraft("en", createDefaultDraft()).spec;
    expect(spec).not.toBeNull();

    const preview = buildPreviewBundle(spec, path.resolve("C:/tmp"), "en", []);

    expect(preview.summary).toContain("plugin: my_device");
    expect(preview.driver).toContain("class MyDeviceDriver");
    expect(preview.pyproject).toContain('license = "MIT"');
    expect(preview.readme).toContain("# MyDevice Driver Plugin");
  });

  test("renders placeholder previews when validation fails", () => {
    const preview = buildPreviewBundle(null, path.resolve("C:/tmp"), "en", ["bad plugin"]);

    expect(preview.summary).toContain("Validation errors");
    expect(preview.driver).toContain("Preview is unavailable");
  });

  test("renders stable project files", () => {
    const spec = validateDraft("en", createDefaultDraft()).spec;
    expect(spec).not.toBeNull();

    expect(renderPyprojectToml(spec!)).toContain('[project.entry-points."modlink.drivers"]');
    expect(renderReadme(spec!, "zh")).toContain("Driver 插件");
    expect(renderLicense()).toContain("MIT License");
  });
});
