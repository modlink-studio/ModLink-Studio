import React from "react";
import {Box, Text} from "ink";

import {getCopy, sectionOrder} from "../lib/i18n.js";
import type {AppState, Language, ValidationResult} from "../lib/types.js";
import type {UiRow} from "./rows.js";

function renderTone(tone: AppState["statusTone"]): "blue" | "red" | "green" {
  if (tone === "error") {
    return "red";
  }
  if (tone === "success") {
    return "green";
  }
  return "blue";
}

type EditorPaneProps = {
  language: Language;
  state: AppState;
  rows: UiRow[];
  validation: ValidationResult;
  ready: boolean;
};

export function EditorPane({language, state, rows, validation, ready}: EditorPaneProps): React.JSX.Element {
  const copy = getCopy(language);
  const selectedStream = state.draft.streams[state.draft.selectedStreamIndex];

  return (
    <Box flexDirection="column" flexGrow={1} paddingRight={1}>
      <Text color="cyan">
        {copy.currentSectionLabel}:{" "}
        {sectionOrder
          .map((section) => (section === state.section ? `[${copy.sections[section]}]` : copy.sections[section]))
          .join("  ")}
      </Text>
      {state.section === "streams" ? (
        <Box flexDirection="column" marginTop={1}>
          <Text color="yellow">{copy.selectedStreamLabel}</Text>
          {state.draft.streams.map((stream, index) => (
            <Text key={`${stream.modality}-${index}`} color={index === state.draft.selectedStreamIndex ? "cyan" : undefined}>
              {index === state.draft.selectedStreamIndex ? ">" : " "} {index + 1}. {stream.displayName || stream.modality}
            </Text>
          ))}
        </Box>
      ) : null}
      <Box flexDirection="column" marginTop={1}>
        {rows.map((row, index) => {
          const active = index === state.rowIndex;
          const prefix = active ? ">" : " ";
          const color = row.error ? "red" : active ? "cyan" : undefined;
          const actionSuffix = row.kind === "action" ? " [Enter]" : row.kind === "choice" ? " [Left/Right]" : "";

          return (
            <Box key={row.key} flexDirection="column" marginBottom={row.error ? 1 : 0}>
              <Text color={color}>
                {prefix} {row.label}: {row.value || "<empty>"}
                {actionSuffix}
              </Text>
              {row.error ? (
                <Text color="red">
                  {"  "}! {row.error}
                </Text>
              ) : null}
            </Box>
          );
        })}
      </Box>
      {state.section === "driver" ? (
        <Box flexDirection="column" marginTop={1}>
          <Text color="yellow">
            {copy.recommendedDriverLabel}: {copy.driverKindOptions[validation.recommendedDriverKind]}
          </Text>
          <Text>{validation.recommendedReason}</Text>
        </Box>
      ) : null}
      {state.section === "streams" ? (
        <Box flexDirection="column" marginTop={1}>
          <Text color="yellow">
            {selectedStream.displayName || selectedStream.modality} · {selectedStream.payloadType}
          </Text>
          <Text dimColor>{copy.streamChannelNamesLabel}: {selectedStream.channelNames || "<empty>"}</Text>
        </Box>
      ) : null}
      <Box flexDirection="column" marginTop={1}>
        <Text color={ready ? "green" : "red"}>{ready ? copy.readyToGenerate : copy.cannotGenerate}</Text>
        {state.statusMessage ? (
          <Text color={renderTone(state.statusTone)}>
            {copy.statusPrefix}: {state.statusMessage}
          </Text>
        ) : null}
      </Box>
    </Box>
  );
}
