import React, {useEffect, useMemo, useReducer, useState} from "react";
import {Box, Text, useApp, useInput, useStdout} from "ink";
import TextInput from "ink-text-input";

import {writeProjectFiles, ScaffoldExistsError} from "./lib/fs.js";
import {getCopy} from "./lib/i18n.js";
import {buildPreviewBundle} from "./templates/render.js";
import {
  addStream,
  createInitialState,
  cycleDataArrival,
  cycleDriverKind,
  cyclePayloadType,
  cycleSelectedStream,
  deleteStream,
  duplicateStream,
  moveStream,
  reducer,
  setSelectedStream,
  updateDraftField,
  updateSelectedStreamField,
} from "./lib/state.js";
import {createDefaultDraft, validateDraft} from "./lib/spec.js";
import type {Draft, GeneratedProject, Language} from "./lib/types.js";
import {EditorPane} from "./ui/EditorPane.js";
import {OverwriteDialog} from "./ui/OverwriteDialog.js";
import {PreviewPane} from "./ui/PreviewPane.js";
import {ResultScreen} from "./ui/ResultScreen.js";
import {getRowsForSection} from "./ui/rows.js";

export type ScaffoldAppProps = {
  language: Language;
  cwd: string;
  initialDraft?: Draft;
  onDidGenerate?: (result: GeneratedProject) => void;
};

function uniqueErrors(errors: Record<string, string>): string[] {
  return Array.from(new Set(Object.values(errors)));
}

export function ScaffoldApp({language, cwd, initialDraft, onDidGenerate}: ScaffoldAppProps): React.JSX.Element {
  const {exit} = useApp();
  const {stdout} = useStdout();
  const [state, dispatch] = useReducer(
    reducer,
    undefined,
    () => ({...createInitialState(), draft: initialDraft ?? createDefaultDraft()}),
  );
  const [busy, setBusy] = useState(false);
  const copy = getCopy(language);
  const validation = useMemo(() => validateDraft(language, state.draft), [language, state.draft]);
  const rows = useMemo(() => getRowsForSection(language, state.section, state.draft, validation), [language, state.section, state.draft, validation]);
  const preview = useMemo(
    () => buildPreviewBundle(validation.spec, cwd, language, uniqueErrors(validation.fieldErrors)),
    [validation, cwd, language],
  );
  const previewLines = Math.max(10, Math.floor((stdout.rows ?? process.stdout.rows ?? 30) - 10));
  const ready = validation.spec !== null;

  useEffect(() => {
    dispatch({type: "row.clamp", rowCount: rows.length});
  }, [rows.length, state.section]);

  const currentRow = rows[state.rowIndex];

  const setStatus = (message: string | null, tone: "info" | "error" | "success" = "info"): void => {
    dispatch({type: "status", message, tone});
  };

  const applyEdit = (key: string, value: string): void => {
    if (key.startsWith("identity.")) {
      const field = key.replace("identity.", "") as "pluginName" | "displayName" | "deviceId";
      dispatch({type: "draft.set", draft: updateDraftField(state.draft, field, value)});
      return;
    }
    if (key === "connection.providersText") {
      dispatch({type: "draft.set", draft: updateDraftField(state.draft, "providersText", value)});
      return;
    }
    if (key === "dependencies.dependenciesText") {
      dispatch({type: "draft.set", draft: updateDraftField(state.draft, "dependenciesText", value)});
      return;
    }
    if (key.startsWith("streams.")) {
      const field = key.replace("streams.", "") as Parameters<typeof updateSelectedStreamField>[1];
      if (field !== "selectedStream" && field !== "add" && field !== "duplicate" && field !== "delete" && field !== "moveUp" && field !== "moveDown") {
        dispatch({type: "draft.set", draft: updateSelectedStreamField(state.draft, field, value)});
      }
    }
  };

  const performGenerate = async (overwrite: boolean): Promise<void> => {
    if (validation.spec === null) {
      setStatus(uniqueErrors(validation.fieldErrors)[0] ?? copy.validationBlocked, "error");
      return;
    }
    setBusy(true);
    try {
      const result = await writeProjectFiles(validation.spec, cwd, language, overwrite);
      dispatch({type: "result.set", result});
      setStatus(copy.generationSucceeded, "success");
      onDidGenerate?.(result);
    } catch (error) {
      if (error instanceof ScaffoldExistsError) {
        dispatch({type: "overwrite.open", path: error.projectDir});
        setStatus(copy.outputExists, "error");
      } else {
        const message = error instanceof Error ? error.message : String(error);
        setStatus(message, "error");
      }
    } finally {
      setBusy(false);
    }
  };

  const activateRow = (): void => {
    if (!currentRow) {
      return;
    }
    if (currentRow.kind === "text") {
      dispatch({type: "edit.start", key: currentRow.key, value: currentRow.value === "<empty>" ? "" : currentRow.value});
      return;
    }
    if (currentRow.key === "streams.add") {
      dispatch({type: "draft.set", draft: addStream(state.draft)});
      return;
    }
    if (currentRow.key === "streams.duplicate") {
      dispatch({type: "draft.set", draft: duplicateStream(state.draft)});
      return;
    }
    if (currentRow.key === "streams.delete") {
      dispatch({type: "draft.set", draft: deleteStream(state.draft)});
      return;
    }
    if (currentRow.key === "streams.moveUp") {
      dispatch({type: "draft.set", draft: moveStream(state.draft, -1)});
      return;
    }
    if (currentRow.key === "streams.moveDown") {
      dispatch({type: "draft.set", draft: moveStream(state.draft, 1)});
      return;
    }
    if (currentRow.kind === "choice") {
      handleChoice(1);
    }
  };

  const handleChoice = (delta: number): void => {
    if (!currentRow) {
      return;
    }
    if (currentRow.key === "connection.dataArrival") {
      dispatch({type: "draft.set", draft: cycleDataArrival(state.draft, delta)});
      return;
    }
    if (currentRow.key === "driver.driverKind") {
      dispatch({type: "draft.set", draft: cycleDriverKind(state.draft, delta)});
      return;
    }
    if (currentRow.key === "streams.selectedStream") {
      dispatch({type: "draft.set", draft: cycleSelectedStream(state.draft, delta)});
      return;
    }
    if (currentRow.key === "streams.payloadType") {
      dispatch({type: "draft.set", draft: cyclePayloadType(state.draft, delta)});
    }
  };

  useInput((input, key) => {
    if (state.result) {
      if (key.return || key.escape || input === "q") {
        exit();
      }
      return;
    }

    if (state.overwritePath) {
      if (key.leftArrow || key.rightArrow || key.tab) {
        dispatch({type: "overwrite.focus", focus: state.overwriteFocus === "cancel" ? "overwrite" : "cancel"});
        return;
      }
      if (key.escape || input === "q") {
        dispatch({type: "overwrite.close"});
        setStatus(copy.overwriteCancelled, "info");
        return;
      }
      if (key.return) {
        if (state.overwriteFocus === "overwrite") {
          void performGenerate(true);
        } else {
          dispatch({type: "overwrite.close"});
          setStatus(copy.overwriteCancelled, "info");
        }
      }
      return;
    }

    if (state.editingKey) {
      if (key.escape) {
        dispatch({type: "edit.cancel"});
      }
      return;
    }

    if (busy) {
      return;
    }

    if (input === "q" || (key.escape && !state.editingKey)) {
      exit();
      return;
    }
    if (input === "g") {
      void performGenerate(false);
      return;
    }
    if (input === "[") {
      dispatch({type: "preview.delta", delta: -1});
      return;
    }
    if (input === "]") {
      dispatch({type: "preview.delta", delta: 1});
      return;
    }
    if (key.tab) {
      dispatch({type: "section.delta", delta: 1});
      return;
    }
    if (key.upArrow) {
      dispatch({type: "row.delta", delta: -1, rowCount: rows.length});
      return;
    }
    if (key.downArrow) {
      dispatch({type: "row.delta", delta: 1, rowCount: rows.length});
      return;
    }
    if (key.leftArrow) {
      handleChoice(-1);
      return;
    }
    if (key.rightArrow) {
      handleChoice(1);
      return;
    }
    if (key.return) {
      activateRow();
      return;
    }
    if (input >= "1" && input <= "9" && state.section === "streams") {
      const index = Number.parseInt(input, 10) - 1;
      dispatch({type: "draft.set", draft: setSelectedStream(state.draft, index)});
    }
  });

  if (state.result) {
    return <ResultScreen language={language} result={state.result} />;
  }

  if (state.overwritePath) {
    return <OverwriteDialog language={language} projectPath={state.overwritePath} focus={state.overwriteFocus} />;
  }

  return (
    <Box flexDirection="column">
      <Text bold color="green">
        {copy.appTitle}
      </Text>
      <Text dimColor>{copy.appSubtitle}</Text>
      <Text dimColor>{copy.helpLine}</Text>
      <Box marginTop={1}>
        <EditorPane language={language} state={state} rows={rows} validation={validation} ready={ready} />
        <PreviewPane language={language} previewTab={state.previewTab} preview={preview} maxLines={previewLines} />
      </Box>
      <Box marginTop={1} flexDirection="column">
        <Text>
          {copy.currentPreviewLabel}: {copy.previewTabs[state.previewTab]} {busy ? "· generating..." : ""}
        </Text>
        {state.editingKey ? (
          <Box>
            <Text color="yellow">edit&gt; </Text>
            <TextInput
              value={state.editBuffer}
              onChange={(value) => dispatch({type: "edit.change", value})}
              onSubmit={(value) => {
                applyEdit(state.editingKey as string, value);
                dispatch({type: "edit.cancel"});
              }}
            />
          </Box>
        ) : (
          <Text dimColor>{cwd}</Text>
        )}
      </Box>
    </Box>
  );
}
