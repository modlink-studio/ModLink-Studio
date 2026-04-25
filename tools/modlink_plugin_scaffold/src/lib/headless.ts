import { z } from "zod";

import { ScaffoldExistsError, writeProjectFiles } from "./fs.js";
import { dataArrivalOrder, driverKindOrder, payloadOrder } from "./i18n.js";
import { validateDraft } from "./spec.js";
import type { Draft, DriverSpec, Language, StreamDraft } from "./types.js";

const payloadValues = ["signal", "raster", "field", "video"] as const;
const dataArrivalValues = ["push", "poll", "unsure"] as const;
const driverKindValues = ["driver", "loop"] as const;

const streamInputSchema = z
  .object({
    streamKey: z.string().min(1),
    displayName: z.string().optional().default(""),
    payloadType: z.enum(payloadValues),
    sampleRateHz: z.number().positive(),
    chunkSize: z.number().int().positive(),
    channelNames: z.array(z.string().min(1)).min(1),
    unit: z.string().optional().default(""),
    rasterLength: z.number().int().positive().optional(),
    fieldHeight: z.number().int().positive().optional(),
    fieldWidth: z.number().int().positive().optional(),
    videoHeight: z.number().int().positive().optional(),
    videoWidth: z.number().int().positive().optional(),
  })
  .strict();

export const scaffoldInputSchema = z
  .object({
    pluginName: z.string().min(1),
    displayName: z.string().optional().default(""),
    deviceId: z.string().optional().default(""),
    providers: z.array(z.string().min(1)).min(1),
    dataArrival: z.enum(dataArrivalValues).default("unsure"),
    driverKind: z.enum(driverKindValues).default("driver"),
    dependencies: z.array(z.string().min(1)).optional().default([]),
    streams: z.array(streamInputSchema).min(1),
  })
  .strict();

type ScaffoldInput = z.infer<typeof scaffoldInputSchema>;

export type HeadlessResult =
  | {
      ok: true;
      spec: DriverSpec;
      projectDir?: string;
      writtenFiles?: string[];
      commands?: Record<string, string>;
    }
  | {
      ok: false;
      errors: Record<string, string>;
      message: string;
    };

export function scaffoldJsonSchema(): object {
  return {
    $schema: "https://json-schema.org/draft/2020-12/schema",
    title: "ModLink Plugin Scaffold Input",
    type: "object",
    additionalProperties: false,
    required: ["pluginName", "providers", "streams"],
    properties: {
      pluginName: { type: "string", minLength: 1 },
      displayName: { type: "string" },
      deviceId: { type: "string", description: "Stable device ID, for example my_device.01." },
      providers: { type: "array", minItems: 1, items: { type: "string", minLength: 1 } },
      dataArrival: { type: "string", enum: dataArrivalOrder, default: "unsure" },
      driverKind: { type: "string", enum: driverKindOrder, default: "driver" },
      dependencies: {
        type: "array",
        items: { type: "string", minLength: 1 },
        default: [],
      },
      streams: {
        type: "array",
        minItems: 1,
        items: {
          type: "object",
          additionalProperties: false,
          required: ["streamKey", "payloadType", "sampleRateHz", "chunkSize", "channelNames"],
          properties: {
            streamKey: { type: "string", minLength: 1 },
            displayName: { type: "string" },
            payloadType: { type: "string", enum: payloadOrder },
            sampleRateHz: { type: "number", exclusiveMinimum: 0 },
            chunkSize: { type: "integer", minimum: 1 },
            channelNames: {
              type: "array",
              minItems: 1,
              items: { type: "string", minLength: 1 },
            },
            unit: { type: "string" },
            rasterLength: { type: "integer", minimum: 1 },
            fieldHeight: { type: "integer", minimum: 1 },
            fieldWidth: { type: "integer", minimum: 1 },
            videoHeight: { type: "integer", minimum: 1 },
            videoWidth: { type: "integer", minimum: 1 },
          },
        },
      },
    },
  };
}

function zodIssuesToErrors(error: z.ZodError): Record<string, string> {
  const errors: Record<string, string> = {};
  for (const issue of error.issues) {
    const key = issue.path.length > 0 ? issue.path.join(".") : "input";
    errors[key] = issue.message;
  }
  return errors;
}

function streamInputToDraft(stream: ScaffoldInput["streams"][number]): StreamDraft {
  return {
    streamKey: stream.streamKey,
    displayName: stream.displayName,
    payloadType: stream.payloadType,
    sampleRateHz: String(stream.sampleRateHz),
    chunkSize: String(stream.chunkSize),
    channelCount: String(stream.channelNames.length),
    channelNames: stream.channelNames.join(", "),
    unit: stream.unit,
    rasterLength: String(stream.rasterLength ?? 128),
    fieldHeight: String(stream.fieldHeight ?? 48),
    fieldWidth: String(stream.fieldWidth ?? 48),
    videoHeight: String(stream.videoHeight ?? 480),
    videoWidth: String(stream.videoWidth ?? 640),
  };
}

export function parseScaffoldInput(
  input: unknown,
): { draft: Draft } | { errors: Record<string, string> } {
  const parsed = scaffoldInputSchema.safeParse(input);
  if (!parsed.success) {
    return { errors: zodIssuesToErrors(parsed.error) };
  }
  const value = parsed.data;
  return {
    draft: {
      pluginName: value.pluginName,
      displayName: value.displayName,
      deviceId: value.deviceId,
      providersText: value.providers.join(", "),
      dataArrival: value.dataArrival,
      driverKind: value.driverKind,
      dependenciesText: value.dependencies.join(", "),
      streams: value.streams.map(streamInputToDraft),
      selectedStreamIndex: 0,
    },
  };
}

export function validateScaffoldInput(language: Language, input: unknown): HeadlessResult {
  const parsed = parseScaffoldInput(input);
  if ("errors" in parsed) {
    return { ok: false, errors: parsed.errors, message: "Input does not match scaffold schema." };
  }
  const validation = validateDraft(language, parsed.draft);
  if (validation.spec === null) {
    return {
      ok: false,
      errors: validation.fieldErrors,
      message: "Scaffold input failed validation.",
    };
  }
  return { ok: true, spec: validation.spec };
}

export async function generateScaffoldProject(
  language: Language,
  input: unknown,
  outDir: string,
  overwrite: boolean,
): Promise<HeadlessResult> {
  const validation = validateScaffoldInput(language, input);
  if (!validation.ok) {
    return validation;
  }
  try {
    const generated = await writeProjectFiles(validation.spec, outDir, language, overwrite);
    return {
      ok: true,
      spec: validation.spec,
      projectDir: generated.projectDir,
      writtenFiles: generated.writtenFiles,
      commands: generated.commands,
    };
  } catch (error) {
    if (error instanceof ScaffoldExistsError) {
      return {
        ok: false,
        errors: { projectDir: error.projectDir },
        message: "Target directory already exists. Pass --overwrite to replace it.",
      };
    }
    return {
      ok: false,
      errors: { error: error instanceof Error ? error.message : String(error) },
      message: "Scaffold generation failed.",
    };
  }
}
