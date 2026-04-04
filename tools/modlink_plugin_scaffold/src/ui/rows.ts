import {getCopy} from "../lib/i18n.js";
import {visibleStreamFieldKeys} from "../lib/spec.js";
import type {Draft, Language, SectionId, UiRowZone, ValidationResult} from "../lib/types.js";

export type RowKind = "text" | "choice" | "action";

export interface UiRow {
  key: string;
  kind: RowKind;
  label: string;
  value: string;
  description: string;
  zone: UiRowZone;
  error?: string;
}

function errorFor(validation: ValidationResult, key: string): string | undefined {
  return validation.fieldErrors[key];
}

function withEditingValue(row: UiRow, editingKey: string | null, editBuffer: string): UiRow {
  if (editingKey !== row.key) {
    return row;
  }
  return {...row, value: editBuffer};
}

export function getRowsForSection(
  language: Language,
  section: SectionId,
  draft: Draft,
  validation: ValidationResult,
  editingKey: string | null,
  editBuffer: string,
): UiRow[] {
  const copy = getCopy(language);
  const selectedStream = draft.streams[draft.selectedStreamIndex];
  const streamPrefix = `streams.${draft.selectedStreamIndex}`;
  const descriptionFor = (key: string): string => {
    if (copy.rowDescriptions[key]) {
      return copy.rowDescriptions[key];
    }
    if (key.startsWith("streams.select.")) {
      return copy.rowDescriptions["streams.select"] ?? "";
    }
    return "";
  };

  if (section === "identity") {
    return [
      {
        key: "identity.pluginName",
        kind: "text",
        label: copy.pluginNameLabel,
        value: draft.pluginName,
        description: descriptionFor("identity.pluginName"),
        zone: "default",
        error: errorFor(validation, "pluginName"),
      },
      {
        key: "identity.displayName",
        kind: "text",
        label: copy.displayNameLabel,
        value: draft.displayName,
        description: descriptionFor("identity.displayName"),
        zone: "default",
      },
      {
        key: "identity.deviceId",
        kind: "text",
        label: copy.deviceIdLabel,
        value: draft.deviceId,
        description: descriptionFor("identity.deviceId"),
        zone: "default",
        error: errorFor(validation, "deviceId"),
      },
    ].map((row) => withEditingValue(row, editingKey, editBuffer));
  }

  if (section === "connection") {
    return [
      {
        key: "connection.providersText",
        kind: "text",
        label: copy.providersLabel,
        value: draft.providersText,
        description: descriptionFor("connection.providersText"),
        zone: "default",
        error: errorFor(validation, "providersText"),
      },
      {
        key: "connection.dataArrival",
        kind: "choice",
        label: copy.dataArrivalLabel,
        value: copy.dataArrivalOptions[draft.dataArrival],
        description: descriptionFor("connection.dataArrival"),
        zone: "default",
      },
    ].map((row) => withEditingValue(row, editingKey, editBuffer));
  }

  if (section === "driver") {
    return [
      {
        key: "driver.driverKind",
        kind: "choice",
        label: copy.driverKindLabel,
        value: copy.driverKindOptions[draft.driverKind],
        description: descriptionFor("driver.driverKind"),
        zone: "default",
      },
    ].map((row) => withEditingValue(row, editingKey, editBuffer));
  }

  if (section === "dependencies") {
    return [
      {
        key: "dependencies.dependenciesText",
        kind: "text",
        label: copy.dependenciesLabel,
        value: draft.dependenciesText,
        description: descriptionFor("dependencies.dependenciesText"),
        zone: "default",
      },
    ].map((row) => withEditingValue(row, editingKey, editBuffer));
  }

  const dynamicFieldLabels: Record<string, string> = {
    channelCount: copy.streamChannelCountLabel,
    channelNames: copy.streamChannelNamesLabel,
    unit: copy.streamUnitLabel,
    rasterLength: copy.streamRasterLengthLabel,
    fieldHeight: copy.streamFieldHeightLabel,
    fieldWidth: copy.streamFieldWidthLabel,
    videoHeight: copy.streamVideoHeightLabel,
    videoWidth: copy.streamVideoWidthLabel,
  };

  return [
    ...draft.streams.map((stream, index) => {
      const defaultName = `${copy.defaultStreamName} ${index + 1}`;
      const streamName = stream.displayName.trim();
      const meta = streamName && streamName !== defaultName ? streamName : copy.payloadOptions[stream.payloadType];
      return {
        key: `streams.select.${index}`,
        kind: "action" as const,
        label: defaultName,
        value: meta,
        description: descriptionFor(`streams.select.${index}`),
        zone: "stream-list" as const,
      };
    }),
    {key: "streams.add", kind: "action", label: copy.streamAddAction, value: "", description: descriptionFor("streams.add"), zone: "stream-action"},
    {key: "streams.delete", kind: "action", label: copy.streamDeleteAction, value: "", description: descriptionFor("streams.delete"), zone: "stream-action"},
    {
      key: "streams.modality",
      kind: "text",
      label: copy.streamModalityLabel,
      value: selectedStream.modality,
      description: descriptionFor("streams.modality"),
      zone: "stream-basic",
      error: errorFor(validation, `${streamPrefix}.modality`),
    },
    {
      key: "streams.displayName",
      kind: "text",
      label: copy.streamDisplayNameLabel,
      value: selectedStream.displayName,
      description: descriptionFor("streams.displayName"),
      zone: "stream-basic",
    },
    {
      key: "streams.payloadType",
      kind: "choice",
      label: copy.streamPayloadLabel,
      value: copy.payloadOptions[selectedStream.payloadType],
      description: descriptionFor("streams.payloadType"),
      zone: "stream-basic",
      error: errorFor(validation, `${streamPrefix}.payloadType`),
    },
    {
      key: "streams.sampleRateHz",
      kind: "text",
      label: copy.streamSampleRateLabel,
      value: selectedStream.sampleRateHz,
      description: descriptionFor("streams.sampleRateHz"),
      zone: "stream-timing",
      error: errorFor(validation, `${streamPrefix}.sampleRateHz`),
    },
    {
      key: "streams.chunkSize",
      kind: "text",
      label: copy.streamChunkSizeLabel,
      value: selectedStream.chunkSize,
      description: descriptionFor("streams.chunkSize"),
      zone: "stream-timing",
      error: errorFor(validation, `${streamPrefix}.chunkSize`),
    },
    ...visibleStreamFieldKeys(selectedStream.payloadType).map((fieldKey) => ({
      key: `streams.${fieldKey}`,
      kind: "text" as const,
      label: dynamicFieldLabels[fieldKey] ?? fieldKey,
      value: String(selectedStream[fieldKey as keyof typeof selectedStream] ?? ""),
      description: descriptionFor(`streams.${fieldKey}`),
      zone: "stream-payload" as const,
      error: errorFor(validation, `${streamPrefix}.${fieldKey}`),
    })),
  ].map((row) => withEditingValue(row, editingKey, editBuffer));
}
