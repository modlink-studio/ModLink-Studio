import { dataArrivalOrder, driverKindOrder, sectionOrder } from "./i18n.js";
import {
  applyDataArrival,
  applyPayloadDefaults,
  applyPluginName,
  createDefaultDraft,
  createDefaultStream,
  validateDraft,
  visibleStreamFieldKeys,
} from "./spec.js";
import type {
  AppState,
  DataArrival,
  Draft,
  ModalFocus,
  PayloadType,
  StreamDraft,
} from "./types.js";

export type Action =
  | { type: "section.delta"; delta: number }
  | { type: "row.delta"; delta: number; rowCount: number }
  | { type: "row.clamp"; rowCount: number }
  | { type: "status"; message: string | null; tone: "info" | "error" | "success" }
  | { type: "edit.start"; key: string }
  | { type: "edit.cancel" }
  | { type: "draft.set"; draft: Draft }
  | { type: "overwrite.open"; path: string }
  | { type: "overwrite.close" }
  | { type: "overwrite.focus"; focus: ModalFocus }
  | { type: "result.set"; result: AppState["result"] }
  | { type: "result.clear" };

export function createInitialState(): AppState {
  return {
    draft: createDefaultDraft(),
    section: "identity",
    rowIndex: 0,
    editingKey: null,
    statusMessage: null,
    statusTone: "info",
    overwritePath: null,
    overwriteFocus: "cancel",
    result: null,
  };
}

export function reducer(state: AppState, action: Action): AppState {
  switch (action.type) {
    case "section.delta": {
      const index = sectionOrder.indexOf(state.section);
      const nextIndex = (index + action.delta + sectionOrder.length) % sectionOrder.length;
      return { ...state, section: sectionOrder[nextIndex], rowIndex: 0, editingKey: null };
    }
    case "row.delta":
      return {
        ...state,
        rowIndex: Math.min(
          Math.max(state.rowIndex + action.delta, 0),
          Math.max(action.rowCount - 1, 0),
        ),
      };
    case "row.clamp":
      return { ...state, rowIndex: Math.min(state.rowIndex, Math.max(action.rowCount - 1, 0)) };
    case "status":
      return { ...state, statusMessage: action.message, statusTone: action.tone };
    case "edit.start":
      return { ...state, editingKey: action.key };
    case "edit.cancel":
      return { ...state, editingKey: null };
    case "draft.set":
      return { ...state, draft: action.draft };
    case "overwrite.open":
      return { ...state, overwritePath: action.path, overwriteFocus: "cancel" };
    case "overwrite.close":
      return { ...state, overwritePath: null, overwriteFocus: "cancel" };
    case "overwrite.focus":
      return { ...state, overwriteFocus: action.focus };
    case "result.set":
      return { ...state, result: action.result, overwritePath: null, editingKey: null };
    case "result.clear":
      return { ...state, result: null };
    default:
      return state;
  }
}

function replaceSelectedStream(draft: Draft, stream: StreamDraft): Draft {
  return {
    ...draft,
    streams: draft.streams.map((item, index) =>
      index === draft.selectedStreamIndex ? stream : item,
    ),
  };
}

export function updateDraftField(
  draft: Draft,
  field: "pluginName" | "displayName" | "deviceId" | "providersText" | "dependenciesText",
  value: string,
): Draft {
  if (field === "pluginName") {
    return applyPluginName(draft, value);
  }
  return { ...draft, [field]: value };
}

export function cycleDataArrival(draft: Draft, delta: number): Draft {
  const index = dataArrivalOrder.indexOf(draft.dataArrival);
  return applyDataArrival(
    draft,
    dataArrivalOrder[
      (index + delta + dataArrivalOrder.length) % dataArrivalOrder.length
    ] as DataArrival,
  );
}

export function cycleDriverKind(draft: Draft, delta: number): Draft {
  const index = driverKindOrder.indexOf(draft.driverKind);
  return {
    ...draft,
    driverKind: driverKindOrder[(index + delta + driverKindOrder.length) % driverKindOrder.length],
  };
}

export function cyclePayloadType(draft: Draft, delta: number): Draft {
  const payloads: PayloadType[] = ["signal", "raster", "field", "video"];
  const stream = draft.streams[draft.selectedStreamIndex];
  const index = payloads.indexOf(stream.payloadType);
  return replaceSelectedStream(
    draft,
    applyPayloadDefaults(stream, payloads[(index + delta + payloads.length) % payloads.length]),
  );
}

export function cycleSelectedStream(draft: Draft, delta: number): Draft {
  if (draft.streams.length === 0) {
    return draft;
  }
  return {
    ...draft,
    selectedStreamIndex:
      (draft.selectedStreamIndex + delta + draft.streams.length) % draft.streams.length,
  };
}

export function setSelectedStream(draft: Draft, index: number): Draft {
  if (index < 0 || index >= draft.streams.length) {
    return draft;
  }
  return { ...draft, selectedStreamIndex: index };
}

export function addStream(draft: Draft): Draft {
  const streams = [...draft.streams, createDefaultStream(draft.streams.length)];
  return { ...draft, streams, selectedStreamIndex: streams.length - 1 };
}

export function duplicateStream(draft: Draft): Draft {
  const duplicate = { ...draft.streams[draft.selectedStreamIndex] };
  const streams = [...draft.streams];
  streams.splice(draft.selectedStreamIndex + 1, 0, duplicate);
  return { ...draft, streams, selectedStreamIndex: draft.selectedStreamIndex + 1 };
}

export function deleteStream(draft: Draft): Draft {
  if (draft.streams.length <= 1) {
    return { ...draft, streams: [createDefaultStream(0)], selectedStreamIndex: 0 };
  }
  const streams = draft.streams.filter((_, index) => index !== draft.selectedStreamIndex);
  return { ...draft, streams, selectedStreamIndex: Math.max(0, draft.selectedStreamIndex - 1) };
}

export function moveStream(draft: Draft, delta: -1 | 1): Draft {
  const targetIndex = draft.selectedStreamIndex + delta;
  if (targetIndex < 0 || targetIndex >= draft.streams.length) {
    return draft;
  }
  const streams = [...draft.streams];
  [streams[draft.selectedStreamIndex], streams[targetIndex]] = [
    streams[targetIndex],
    streams[draft.selectedStreamIndex],
  ];
  return { ...draft, streams, selectedStreamIndex: targetIndex };
}

export function updateSelectedStreamField(
  draft: Draft,
  field: keyof StreamDraft,
  value: string,
): Draft {
  const stream = draft.streams[draft.selectedStreamIndex];
  const updated =
    field === "payloadType"
      ? applyPayloadDefaults(stream, value as PayloadType)
      : { ...stream, [field]: value };
  const withField = replaceSelectedStream(draft, updated);
  if (field === "channelCount") {
    const parsed = Number.parseInt(value, 10);
    if (Number.isInteger(parsed) && parsed > 0) {
      return replaceSelectedStream(withField, {
        ...updated,
        channelNames: Array.from({ length: parsed }, (_, index) => `ch${index + 1}`).join(", "),
      });
    }
  }
  return withField;
}

export function getFirstErrorMessage(
  language: Parameters<typeof validateDraft>[0],
  draft: Draft,
): string | null {
  return Object.values(validateDraft(language, draft).fieldErrors)[0] ?? null;
}

export function getVisibleStreamFields(payloadType: PayloadType): string[] {
  return visibleStreamFieldKeys(payloadType);
}
