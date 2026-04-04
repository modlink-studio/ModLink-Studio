import {z} from "zod";

import {dataArrivalOrder, driverKindOrder, getCopy, payloadOrder} from "./i18n.js";
import type {DataArrival, Draft, DriverKind, DriverSpec, Language, PayloadType, StreamDraft, StreamSpec, ValidationResult} from "./types.js";

const deviceIdPattern = /^[a-z0-9_]+\.[0-9]{2,}$/;
const stringSchema = z.string();

export function createDefaultStream(index: number): StreamDraft {
  const labelIndex = index + 1;
  return {
    modality: `stream_${labelIndex}`,
    displayName: `Stream ${labelIndex}`,
    payloadType: "signal",
    sampleRateHz: "250",
    chunkSize: "25",
    channelCount: "2",
    channelNames: "ch1, ch2",
    unit: "",
    rasterLength: "128",
    fieldHeight: "48",
    fieldWidth: "48",
    videoHeight: "480",
    videoWidth: "640",
  };
}

export function createDefaultDraft(): Draft {
  return {
    pluginName: "my-device",
    displayName: "",
    deviceId: "",
    providersText: "serial",
    dataArrival: "unsure",
    driverKind: "driver",
    dependenciesText: "",
    streams: [createDefaultStream(0)],
    selectedStreamIndex: 0,
  };
}

export function sanitizeIdentifier(value: string): string {
  const normalized = String(value)
    .replace(/[^\w\s-]/g, "")
    .replace(/[-\s]+/g, "_")
    .toLowerCase()
    .replace(/^_+|_+$/g, "");
  if (!normalized) {
    return "";
  }
  return /^\d/.test(normalized) ? `plugin_${normalized}` : normalized;
}

export function normalizeToken(value: string): string {
  return String(value)
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_]+/g, "_")
    .replace(/_+/g, "_")
    .replace(/^_+|_+$/g, "");
}

export function toPascalCase(value: string): string {
  return String(value)
    .split(/[_-]+/g)
    .filter(Boolean)
    .map((part) => `${part[0]?.toUpperCase() ?? ""}${part.slice(1)}`)
    .join("");
}

export function toTitleWords(value: string): string {
  return normalizeToken(value)
    .split("_")
    .filter(Boolean)
    .map((part) => `${part[0]?.toUpperCase() ?? ""}${part.slice(1)}`)
    .join(" ");
}

export function makeDeviceId(pluginName: string): string {
  const normalized = normalizeToken(pluginName);
  return normalized ? `${normalized}.01` : "";
}

export function splitCsv(value: string): string[] {
  const items = String(value)
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
  return Array.from(new Set(items));
}

export function positiveInt(value: string): number | null {
  const parsed = Number.parseInt(String(value).trim(), 10);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
}

export function positiveFloat(value: string): number | null {
  const parsed = Number.parseFloat(String(value).trim());
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

export function recommendedDriverKind(dataArrival: DataArrival): DriverKind {
  return dataArrival === "poll" ? "loop" : "driver";
}

export function driverReason(language: Language, dataArrival: DataArrival, driverKind: DriverKind): string {
  const copy = getCopy(language);
  if (dataArrival === "push") {
    return driverKind === "driver" ? copy.reasonPushDriver : copy.reasonPushLoop;
  }
  if (dataArrival === "poll") {
    return driverKind === "loop" ? copy.reasonPollLoop : copy.reasonPollDriver;
  }
  return driverKind === "driver" ? copy.reasonUnsureDriver : copy.reasonUnsureLoop;
}

export function applyPluginName(draft: Draft, value: string): Draft {
  const previousPluginName = draft.pluginName;
  const previousDefaultDisplay = toPascalCase(sanitizeIdentifier(previousPluginName) || previousPluginName);
  const previousDefaultDeviceId = makeDeviceId(previousPluginName);
  const normalized = sanitizeIdentifier(value);

  return {
    ...draft,
    pluginName: value,
    displayName:
      !draft.displayName.trim() || draft.displayName === previousDefaultDisplay
        ? (normalized ? toPascalCase(normalized) : "")
        : draft.displayName,
    deviceId:
      !draft.deviceId.trim() || draft.deviceId === previousDefaultDeviceId
        ? makeDeviceId(value)
        : draft.deviceId,
  };
}

export function applyDataArrival(draft: Draft, value: DataArrival): Draft {
  if (!dataArrivalOrder.includes(value)) {
    return draft;
  }
  const previousRecommended = recommendedDriverKind(draft.dataArrival);
  return {
    ...draft,
    dataArrival: value,
    driverKind: draft.driverKind === previousRecommended ? recommendedDriverKind(value) : draft.driverKind,
  };
}

export function applyPayloadDefaults(stream: StreamDraft, payloadType: PayloadType): StreamDraft {
  if (payloadType === "signal") {
    return {
      ...stream,
      payloadType,
      sampleRateHz: "250",
      chunkSize: "25",
      channelCount: "2",
      channelNames: "ch1, ch2",
    };
  }
  if (payloadType === "raster") {
    return {
      ...stream,
      payloadType,
      sampleRateHz: "10",
      chunkSize: "1",
      channelCount: "1",
      channelNames: "intensity",
      rasterLength: "128",
    };
  }
  if (payloadType === "field") {
    return {
      ...stream,
      payloadType,
      sampleRateHz: "10",
      chunkSize: "1",
      channelCount: "1",
      channelNames: "intensity",
      fieldHeight: "48",
      fieldWidth: "48",
    };
  }
  return {
    ...stream,
    payloadType,
    sampleRateHz: "30",
    chunkSize: "1",
    channelCount: "3",
    channelNames: "red, green, blue",
    videoHeight: "480",
    videoWidth: "640",
    unit: "",
  };
}

function validateStream(language: Language, stream: StreamDraft, index: number, fieldErrors: Record<string, string>): StreamSpec | null {
  const copy = getCopy(language);
  const prefix = `streams.${index}`;
  const modality = normalizeToken(stream.modality);

  if (!modality) {
    fieldErrors[`${prefix}.modality`] = copy.modalityError;
  }

  if (!payloadOrder.includes(stream.payloadType)) {
    fieldErrors[`${prefix}.payloadType`] = copy.validationBlocked;
    return null;
  }

  const sampleRateHz = positiveFloat(stream.sampleRateHz);
  if (sampleRateHz === null) {
    fieldErrors[`${prefix}.sampleRateHz`] = copy.positiveFloatError;
  }

  const chunkSize = positiveInt(stream.chunkSize);
  if (chunkSize === null) {
    fieldErrors[`${prefix}.chunkSize`] = copy.positiveIntError;
  }

  const channelNames = splitCsv(stream.channelNames);
  if (channelNames.length === 0) {
    fieldErrors[`${prefix}.channelNames`] = copy.channelNamesError;
  }

  const channelCount = positiveInt(stream.channelCount);
  if (stream.payloadType === "signal") {
    if (channelCount === null) {
      fieldErrors[`${prefix}.channelCount`] = copy.positiveIntError;
    } else if (channelNames.length > 0 && channelNames.length !== channelCount) {
      fieldErrors[`${prefix}.channelNames`] = copy.signalChannelNamesCountError;
    }
  }

  const rasterLength = stream.payloadType === "raster" ? positiveInt(stream.rasterLength) : null;
  if (stream.payloadType === "raster" && rasterLength === null) {
    fieldErrors[`${prefix}.rasterLength`] = copy.positiveIntError;
  }

  const fieldHeight = stream.payloadType === "field" ? positiveInt(stream.fieldHeight) : null;
  const fieldWidth = stream.payloadType === "field" ? positiveInt(stream.fieldWidth) : null;
  if (stream.payloadType === "field") {
    if (fieldHeight === null) {
      fieldErrors[`${prefix}.fieldHeight`] = copy.positiveIntError;
    }
    if (fieldWidth === null) {
      fieldErrors[`${prefix}.fieldWidth`] = copy.positiveIntError;
    }
  }

  const videoHeight = stream.payloadType === "video" ? positiveInt(stream.videoHeight) : null;
  const videoWidth = stream.payloadType === "video" ? positiveInt(stream.videoWidth) : null;
  if (stream.payloadType === "video") {
    if (videoHeight === null) {
      fieldErrors[`${prefix}.videoHeight`] = copy.positiveIntError;
    }
    if (videoWidth === null) {
      fieldErrors[`${prefix}.videoWidth`] = copy.positiveIntError;
    }
  }

  if (Object.keys(fieldErrors).some((key) => key.startsWith(`${prefix}.`))) {
    return null;
  }

  return {
    modality,
    displayName: stringSchema.parse(stream.displayName).trim() || `${toTitleWords(modality)} ${copy.defaultStreamName}`,
    payloadType: stream.payloadType,
    sampleRateHz: sampleRateHz ?? 1,
    chunkSize: chunkSize ?? 1,
    channelNames,
    unit: stream.unit.trim() || undefined,
    rasterLength: rasterLength ?? undefined,
    fieldHeight: fieldHeight ?? undefined,
    fieldWidth: fieldWidth ?? undefined,
    videoHeight: videoHeight ?? undefined,
    videoWidth: videoWidth ?? undefined,
  };
}

export function validateDraft(language: Language, draft: Draft): ValidationResult {
  const copy = getCopy(language);
  const fieldErrors: Record<string, string> = {};

  const pluginName = sanitizeIdentifier(draft.pluginName);
  if (!pluginName) {
    fieldErrors.pluginName = copy.pluginNameError;
  }

  const deviceId = (draft.deviceId.trim() || makeDeviceId(draft.pluginName)).trim().toLowerCase().replace(/-/g, "_");
  if (!deviceIdPattern.test(deviceId)) {
    fieldErrors.deviceId = copy.deviceIdError;
  }

  const providers = splitCsv(draft.providersText).map(normalizeToken).filter(Boolean);
  if (providers.length === 0) {
    fieldErrors.providersText = copy.providersError;
  }

  if (draft.streams.length === 0) {
    fieldErrors.streams = copy.streamsRequiredError;
  }

  const streamSpecs = draft.streams
    .map((stream, index) => validateStream(language, stream, index, fieldErrors))
    .filter((stream): stream is StreamSpec => stream !== null);

  let spec: DriverSpec | null = null;
  if (Object.keys(fieldErrors).length === 0) {
    spec = {
      pluginName,
      projectName: pluginName.replace(/_/g, "-"),
      className: toPascalCase(pluginName),
      displayName: draft.displayName.trim() || toPascalCase(pluginName),
      deviceId,
      providers,
      driverKind: driverKindOrder.includes(draft.driverKind) ? draft.driverKind : "driver",
      driverReason: driverReason(language, draft.dataArrival, draft.driverKind),
      dataArrival: draft.dataArrival,
      dependencies: Array.from(new Set(["modlink-sdk", "numpy>=2.3.3", ...splitCsv(draft.dependenciesText)])),
      streams: streamSpecs,
    };
  }

  return {
    spec,
    fieldErrors,
    recommendedDriverKind: recommendedDriverKind(draft.dataArrival),
    recommendedReason: driverReason(language, draft.dataArrival, recommendedDriverKind(draft.dataArrival)),
  };
}

export function visibleStreamFieldKeys(payloadType: PayloadType): string[] {
  if (payloadType === "signal") {
    return ["channelCount", "channelNames", "unit"];
  }
  if (payloadType === "raster") {
    return ["channelNames", "unit", "rasterLength"];
  }
  if (payloadType === "field") {
    return ["channelNames", "unit", "fieldHeight", "fieldWidth"];
  }
  return ["channelNames", "videoHeight", "videoWidth"];
}
