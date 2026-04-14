export type Language = "en" | "zh";
export type DriverKind = "driver" | "loop";
export type DataArrival = "push" | "poll" | "unsure";
export type PayloadType = "signal" | "raster" | "field" | "video";
export type SectionId = "identity" | "connection" | "driver" | "streams" | "dependencies";
export type ModalFocus = "cancel" | "overwrite";
export type UiRowZone =
  | "default"
  | "stream-list"
  | "stream-action"
  | "stream-basic"
  | "stream-timing"
  | "stream-payload";

export interface StreamDraft {
  streamKey: string;
  displayName: string;
  payloadType: PayloadType;
  sampleRateHz: string;
  chunkSize: string;
  channelCount: string;
  channelNames: string;
  unit: string;
  rasterLength: string;
  fieldHeight: string;
  fieldWidth: string;
  videoHeight: string;
  videoWidth: string;
}

export interface Draft {
  pluginName: string;
  displayName: string;
  deviceId: string;
  providersText: string;
  dataArrival: DataArrival;
  driverKind: DriverKind;
  dependenciesText: string;
  streams: StreamDraft[];
  selectedStreamIndex: number;
}

export interface StreamSpec {
  streamKey: string;
  displayName: string;
  payloadType: PayloadType;
  sampleRateHz: number;
  chunkSize: number;
  channelNames: string[];
  unit?: string;
  rasterLength?: number;
  fieldHeight?: number;
  fieldWidth?: number;
  videoHeight?: number;
  videoWidth?: number;
}

export interface DriverSpec {
  pluginName: string;
  projectName: string;
  className: string;
  displayName: string;
  deviceId: string;
  providers: string[];
  driverKind: DriverKind;
  driverReason: string;
  dataArrival: DataArrival;
  dependencies: string[];
  streams: StreamSpec[];
}

export interface ValidationResult {
  spec: DriverSpec | null;
  fieldErrors: Record<string, string>;
  recommendedDriverKind: DriverKind;
  recommendedReason: string;
}

export interface SummaryHero {
  displayName: string;
  pluginName: string;
  deviceId: string;
}

export interface SummaryMetric {
  label: string;
  value: string;
}

export type SummaryViewModel =
  | {
      kind: "ready";
      title: string;
      hero: SummaryHero;
      metrics: SummaryMetric[];
    }
  | {
      kind: "invalid";
      title: string;
      message: string;
      errors: string[];
    };

export interface PreviewBundle {
  summary: SummaryViewModel;
  driver: string;
  pyproject: string;
  readme: string;
}

export interface GeneratedProject {
  projectDir: string;
  writtenFiles: string[];
  commands: {
    install: string;
    test: string;
    runHost: string;
    checkEntryPoints: string;
  };
}

export interface AppState {
  draft: Draft;
  section: SectionId;
  rowIndex: number;
  editingKey: string | null;
  statusMessage: string | null;
  statusTone: "info" | "error" | "success";
  overwritePath: string | null;
  overwriteFocus: ModalFocus;
  result: GeneratedProject | null;
}
