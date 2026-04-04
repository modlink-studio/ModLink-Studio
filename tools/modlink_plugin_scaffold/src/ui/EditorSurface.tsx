import React from "react";

import type {Draft, Language, SectionId, ValidationResult} from "../lib/types.js";
import {EditorPane} from "./EditorPane.js";
import type {UiRow} from "./rows.js";

type EditorSurfaceProps = {
  language: Language;
  section: SectionId;
  draft: Draft;
  rowIndex: number;
  rows: UiRow[];
  validation: ValidationResult;
  maxRows: number;
  width: number;
  editingKey: string | null;
  editingValue: string;
};

export const EditorSurface = React.memo(function EditorSurface(props: EditorSurfaceProps): React.JSX.Element {
  return <EditorPane {...props} />;
});
