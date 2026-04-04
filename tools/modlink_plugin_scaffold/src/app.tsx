import React, {useEffect, useMemo, useReducer, useState} from "react";
import {Box, Text, useApp, useInput, useStdout} from "ink";

import {writeProjectFiles, ScaffoldExistsError} from "./lib/fs.js";
import {getCopy, sectionOrder} from "./lib/i18n.js";
import {buildPreviewBundle} from "./templates/render.js";
import {
  addStream,
  createInitialState,
  cycleDataArrival,
  cycleDriverKind,
  cyclePayloadType,
  deleteStream,
  reducer,
  setSelectedStream,
  updateDraftField,
  updateSelectedStreamField,
} from "./lib/state.js";
import {createDefaultDraft, validateDraft} from "./lib/spec.js";
import type {Draft, GeneratedProject, Language} from "./lib/types.js";
import {Banner} from "./ui/Banner.js";
import {EditorPane} from "./ui/EditorPane.js";
import {OverwriteDialog} from "./ui/OverwriteDialog.js";
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
  const rows = useMemo(
    () => getRowsForSection(language, state.section, state.draft, validation, state.editingKey, state.editBuffer),
    [language, state.section, state.draft, validation, state.editingKey, state.editBuffer],
  );
  const preview = useMemo(
    () => buildPreviewBundle(validation.spec, cwd, language, uniqueErrors(validation.fieldErrors)),
    [validation, cwd, language],
  );
  const screenWidth = Math.max(80, stdout.columns ?? process.stdout.columns ?? 100);
  const screenHeight = Math.max(24, stdout.rows ?? process.stdout.rows ?? 30);
  const bannerHeight = 5;
  const footerHeight = 2;
  const contentHeight = Math.max(9, screenHeight - 12);
  const editorRows = Math.max(6, contentHeight - (state.section === "streams" ? Math.min(8, state.draft.streams.length + 5) : 6));
  const ready = validation.spec !== null;
  const errorCount = Object.keys(validation.fieldErrors).length;

  useEffect(() => {
    dispatch({type: "row.clamp", rowCount: rows.length});
  }, [rows.length, state.section]);

  const currentRow = rows[state.rowIndex];
  const shortStatus = ready ? copy.readyShort : `${errorCount} ${copy.issuesShort}`;

  const setStatus = (message: string | null, tone: "info" | "error" | "success" = "info"): void => {
    dispatch({type: "status", message, tone});
  };

  const commitEdit = (): void => {
    if (!state.editingKey) {
      return;
    }
    applyEdit(state.editingKey, state.editBuffer);
    dispatch({type: "edit.cancel"});
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
      if (field !== "add" && field !== "delete" && !field.startsWith("select.")) {
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
    if (currentRow.key.startsWith("streams.select.")) {
      const index = Number.parseInt(currentRow.key.split(".").at(-1) ?? "-1", 10);
      dispatch({type: "draft.set", draft: setSelectedStream(state.draft, index)});
      return;
    }
    if (currentRow.key === "streams.add") {
      dispatch({type: "draft.set", draft: addStream(state.draft)});
      return;
    }
    if (currentRow.key === "streams.delete") {
      dispatch({type: "draft.set", draft: deleteStream(state.draft)});
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
      if (key.return) {
        commitEdit();
        return;
      }
      if (key.escape) {
        dispatch({type: "edit.cancel"});
        return;
      }
      if (key.backspace || key.delete) {
        dispatch({type: "edit.change", value: state.editBuffer.slice(0, -1)});
        return;
      }
      if (input && !key.ctrl && !key.meta && !key.tab) {
        dispatch({type: "edit.change", value: state.editBuffer + input});
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
    return <ResultScreen language={language} result={state.result} width={screenWidth} height={screenHeight} />;
  }

  if (state.overwritePath) {
    return <OverwriteDialog language={language} projectPath={state.overwritePath} focus={state.overwriteFocus} width={screenWidth} height={screenHeight} />;
  }

  return (
    <Box width={screenWidth} height={screenHeight} borderStyle="round" borderColor="green" flexDirection="column" paddingX={1}>
      <Box justifyContent="space-between">
        <Text bold color="green">
          {copy.appTitle}
        </Text>
        <Text color={ready ? "green" : "red"}>
          {shortStatus} {busy ? "| generating" : ""}
        </Text>
      </Box>
      <Box>
        {sectionOrder.map((section) => (
          <Box key={section} flexGrow={1} justifyContent="center">
            <Text color={section === state.section ? "cyan" : "gray"} bold={section === state.section}>
              {section === state.section ? `[${copy.sections[section]}]` : copy.sections[section]}
            </Text>
          </Box>
        ))}
      </Box>
      <Text dimColor wrap="truncate-end">
        {copy.sectionDescriptions[state.section]}
      </Text>
      <Box height={bannerHeight}>
        <Banner language={language} summary={preview.summary} width={screenWidth - 4} />
      </Box>
      <Box flexGrow={1} height={contentHeight} borderTop borderBottom borderColor="gray">
        <Box flexGrow={1} paddingRight={1}>
          <EditorPane language={language} state={state} rows={rows} validation={validation} maxRows={editorRows} width={screenWidth - 6} />
        </Box>
      </Box>
      <Box flexDirection="column" height={footerHeight} justifyContent="center">
        {state.editingKey ? (
          <>
            <Text color="yellow" wrap="truncate-end">
              {copy.editingLabel}&gt; {state.editBuffer}
              <Text color="white">█</Text>
            </Text>
            <Text dimColor wrap="truncate-end">
              {copy.controlsLabel}: {copy.footerEditHint}
            </Text>
          </>
        ) : (
          <>
            <Text dimColor wrap="truncate-middle">
              {copy.locationLabel}: {state.statusMessage ?? cwd}
            </Text>
            <Text dimColor wrap="truncate-end">
              {copy.controlsLabel}: {copy.footerIdleHint}
            </Text>
          </>
        )}
      </Box>
    </Box>
  );
}
