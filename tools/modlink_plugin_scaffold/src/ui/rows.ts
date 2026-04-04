import {getCopy} from "../lib/i18n.js";
import {visibleStreamFieldKeys} from "../lib/spec.js";
import type {Draft, Language, SectionId, ValidationResult} from "../lib/types.js";

export type RowKind = "text" | "choice" | "action";

export interface UiRow {
  key: string;
  kind: RowKind;
  label: string;
  value: string;
  error?: string;
}

function errorFor(validation: ValidationResult, key: string): string | undefined {
  return validation.fieldErrors[key];
}

export function getRowsForSection(language: Language, section: SectionId, draft: Draft, validation: ValidationResult): UiRow[] {
  const copy = getCopy(language);
  const selectedStream = draft.streams[draft.selectedStreamIndex];
  const streamPrefix = `streams.${draft.selectedStreamIndex}`;

  if (section === "identity") {
    return [
      {
        key: "identity.pluginName",
        kind: "text",
        label: copy.pluginNameLabel,
        value: draft.pluginName,
        error: errorFor(validation, "pluginName"),
      },
      {
        key: "identity.displayName",
        kind: "text",
        label: copy.displayNameLabel,
        value: draft.displayName,
      },
      {
        key: "identity.deviceId",
        kind: "text",
        label: copy.deviceIdLabel,
        value: draft.deviceId,
        error: errorFor(validation, "deviceId"),
      },
    ];
  }

  if (section === "connection") {
    return [
      {
        key: "connection.providersText",
        kind: "text",
        label: copy.providersLabel,
        value: draft.providersText,
        error: errorFor(validation, "providersText"),
      },
      {
        key: "connection.dataArrival",
        kind: "choice",
        label: copy.dataArrivalLabel,
        value: copy.dataArrivalOptions[draft.dataArrival],
      },
    ];
  }

  if (section === "driver") {
    return [
      {
        key: "driver.driverKind",
        kind: "choice",
        label: copy.driverKindLabel,
        value: copy.driverKindOptions[draft.driverKind],
      },
    ];
  }

  if (section === "dependencies") {
    return [
      {
        key: "dependencies.dependenciesText",
        kind: "text",
        label: copy.dependenciesLabel,
        value: draft.dependenciesText,
      },
    ];
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
    {
      key: "streams.selectedStream",
      kind: "choice",
      label: copy.selectedStreamLabel,
      value: `${draft.selectedStreamIndex + 1}/${draft.streams.length} ${selectedStream.displayName || selectedStream.modality}`,
    },
    {key: "streams.add", kind: "action", label: copy.streamAddAction, value: ""},
    {key: "streams.duplicate", kind: "action", label: copy.streamDuplicateAction, value: ""},
    {key: "streams.delete", kind: "action", label: copy.streamDeleteAction, value: ""},
    {key: "streams.moveUp", kind: "action", label: copy.streamMoveUpAction, value: ""},
    {key: "streams.moveDown", kind: "action", label: copy.streamMoveDownAction, value: ""},
    {
      key: "streams.modality",
      kind: "text",
      label: copy.streamModalityLabel,
      value: selectedStream.modality,
      error: errorFor(validation, `${streamPrefix}.modality`),
    },
    {
      key: "streams.displayName",
      kind: "text",
      label: copy.streamDisplayNameLabel,
      value: selectedStream.displayName,
    },
    {
      key: "streams.payloadType",
      kind: "choice",
      label: copy.streamPayloadLabel,
      value: copy.payloadOptions[selectedStream.payloadType],
      error: errorFor(validation, `${streamPrefix}.payloadType`),
    },
    {
      key: "streams.sampleRateHz",
      kind: "text",
      label: copy.streamSampleRateLabel,
      value: selectedStream.sampleRateHz,
      error: errorFor(validation, `${streamPrefix}.sampleRateHz`),
    },
    {
      key: "streams.chunkSize",
      kind: "text",
      label: copy.streamChunkSizeLabel,
      value: selectedStream.chunkSize,
      error: errorFor(validation, `${streamPrefix}.chunkSize`),
    },
    ...visibleStreamFieldKeys(selectedStream.payloadType).map((fieldKey) => ({
      key: `streams.${fieldKey}`,
      kind: fieldKey === "channelCount" ? "text" : "text",
      label: dynamicFieldLabels[fieldKey] ?? fieldKey,
      value: String(selectedStream[fieldKey as keyof typeof selectedStream] ?? ""),
      error: errorFor(validation, `${streamPrefix}.${fieldKey}`),
    })),
  ];
}
