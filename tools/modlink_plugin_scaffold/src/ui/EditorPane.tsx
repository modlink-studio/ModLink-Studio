import React from "react";
import {Box, Text} from "ink";

import {getCopy} from "../lib/i18n.js";
import type {AppState, Language, ValidationResult} from "../lib/types.js";
import type {UiRow} from "./rows.js";

type EditorPaneProps = {
  language: Language;
  state: AppState;
  rows: UiRow[];
  validation: ValidationResult;
  maxRows: number;
  width: number;
};

function getWindowedRows(rows: UiRow[], rowIndex: number, maxRows: number): UiRow[] {
  if (rows.length <= maxRows) {
    return rows;
  }
  const half = Math.floor(maxRows / 2);
  const start = Math.max(0, Math.min(rowIndex - half, rows.length - maxRows));
  return rows.slice(start, start + maxRows);
}

function visualWidth(value: string): number {
  return Array.from(value).reduce((sum, char) => sum + (char.charCodeAt(0) > 0xff ? 2 : 1), 0);
}

function padToVisualWidth(value: string, width: number): string {
  const padding = Math.max(0, width - visualWidth(value));
  return `${value}${" ".repeat(padding)}`;
}

function rowDisplayValue(row: UiRow, choiceSwitchHint: string): string {
  const base = row.value || "<empty>";
  if (row.kind === "choice") {
    return `${base} ${choiceSwitchHint}`;
  }
  return base;
}

function renderAlignedRows(rows: UiRow[], activeKey: string | null, labelWidth: number, choiceSwitchHint: string): React.JSX.Element[] {
  return rows.map((row) => {
    const active = activeKey === row.key;
    const prefix = active ? ">" : " ";
    const color = row.error ? "red" : active ? "cyan" : undefined;
    return (
      <Box key={row.key} flexDirection="column">
        <Box>
          <Box width={2}>
            <Text color={color}>{prefix}</Text>
          </Box>
          <Box width={labelWidth + 2}>
            <Text color={color} bold>
              {padToVisualWidth(row.label, labelWidth)}
            </Text>
          </Box>
          <Box flexGrow={1}>
            <Text color={color} wrap="truncate-end">
              {rowDisplayValue(row, choiceSwitchHint)}
            </Text>
          </Box>
        </Box>
        {row.error ? (
          <Text color="red">
            {" ".repeat(labelWidth + 3)}! {row.error}
          </Text>
        ) : null}
      </Box>
    );
  });
}

function activeGroupInfo(
  copy: ReturnType<typeof getCopy>,
  section: AppState["section"],
  row: UiRow | undefined,
): {title: string; description: string} {
  if (section !== "streams" || !row) {
    return {
      title: copy.sections[section],
      description: copy.sectionDescriptions[section],
    };
  }

  switch (row.zone) {
    case "stream-list":
      return {title: copy.streamListTitle, description: copy.streamListDescription};
    case "stream-action":
      return {title: copy.controlsLabel, description: copy.streamActionsDescription};
    case "stream-basic":
      return {title: copy.streamBasicGroupTitle, description: copy.streamBasicGroupDescription};
    case "stream-timing":
      return {title: copy.streamTimingGroupTitle, description: copy.streamTimingGroupDescription};
    case "stream-payload":
      return {title: copy.streamPayloadGroupTitle, description: copy.streamPayloadGroupDescription};
    default:
      return {title: copy.sections[section], description: copy.sectionDescriptions[section]};
  }
}

function renderGroup(
  title: string,
  rows: UiRow[],
  activeKey: string | null,
  labelWidth: number,
  choiceSwitchHint: string,
): React.JSX.Element | null {
  if (rows.length === 0) {
    return null;
  }

  return (
    <Box flexDirection="column" marginTop={1}>
      {rows.map((row, index) => {
        const active = activeKey === row.key;
        const prefix = active ? ">" : " ";
        const color = row.error ? "red" : active ? "cyan" : undefined;
        const groupLabelWidth = 10;
        return (
          <Box key={row.key} flexDirection="column">
            <Box>
              <Box width={groupLabelWidth}>
                <Text color={index === 0 ? "yellow" : undefined} bold={index === 0}>
                  {index === 0 ? title : ""}
                </Text>
              </Box>
              <Box width={2}>
                <Text color={color}>{prefix}</Text>
              </Box>
              <Box width={labelWidth + 2}>
                <Text color={color} bold>
                  {padToVisualWidth(row.label, labelWidth)}
                </Text>
              </Box>
              <Box flexGrow={1}>
                <Text color={color} wrap="truncate-end">
                  {rowDisplayValue(row, choiceSwitchHint)}
                </Text>
              </Box>
            </Box>
            {row.error ? (
              <Text color="red">
                {" ".repeat(groupLabelWidth + labelWidth + 3)}! {row.error}
              </Text>
            ) : null}
          </Box>
        );
      })}
    </Box>
  );
}

function StreamsLayout({
  language,
  state,
  rows,
  width,
}: {
  language: Language;
  state: AppState;
  rows: UiRow[];
  width: number;
}): React.JSX.Element {
  const copy = getCopy(language);
  const currentRow = rows[state.rowIndex];
  const listRows = rows.filter((row) => row.zone === "stream-list");
  const actionRows = rows.filter((row) => row.zone === "stream-action");
  const basicRows = rows.filter((row) => row.zone === "stream-basic");
  const timingRows = rows.filter((row) => row.zone === "stream-timing");
  const payloadRows = rows.filter((row) => row.zone === "stream-payload");
  const currentStream = state.draft.streams[state.draft.selectedStreamIndex];
  const gap = 2;
  const leftWidth = Math.max(26, Math.min(32, Math.floor(width * 0.3)));
  const rightWidth = Math.max(40, width - leftWidth - gap);
  const rightLabelWidth = Math.max(
    14,
    Math.min(
      22,
      ...[...basicRows, ...timingRows, ...payloadRows].map((row) => visualWidth(row.label)),
    ),
  );

  return (
    <Box flexGrow={1}>
      <Box width={leftWidth} borderStyle="round" borderColor="gray" paddingX={1} flexDirection="column">
        <Text color="yellow" bold>
          [{copy.streamListTitle}]
        </Text>
        <Text dimColor wrap="truncate-end">
          {copy.streamListDescription}
        </Text>
        <Box flexDirection="column">
          {listRows.map((row, index) => {
            const active = row.key === currentRow?.key;
            const selected = index === state.draft.selectedStreamIndex;
            const prefix = active ? ">" : selected ? "*" : " ";
            const color = active ? "cyan" : selected ? "green" : undefined;
            return (
              <Text key={row.key} color={color} wrap="truncate-end">
                {prefix} {row.label}
                <Text dimColor>  {row.value}</Text>
              </Text>
            );
          })}
        </Box>
        <Box marginTop={1}>
          <Text color="yellow" bold>
            [{copy.controlsLabel}]
          </Text>
        </Box>
        <Text dimColor>{copy.streamActionsDescription}</Text>
        <Box flexDirection="column">
          {actionRows.map((row) => {
            const active = row.key === currentRow?.key;
            return (
              <Text key={row.key} color={active ? "cyan" : undefined}>
                {active ? ">" : " "} {row.label}
              </Text>
            );
          })}
        </Box>
      </Box>
      <Box width={gap} />
      <Box width={rightWidth} borderStyle="round" borderColor="gray" paddingX={1} flexDirection="column">
        <Text wrap="truncate-end">
          <Text color="yellow" bold>
            [{copy.streamDetailsTitle}]
          </Text>
          <Text dimColor>  {currentStream.displayName || currentStream.modality}</Text>
          <Text dimColor> · {copy.payloadOptions[currentStream.payloadType]}</Text>
        </Text>
        {renderGroup(copy.streamBasicGroupTitle, basicRows, currentRow?.key ?? null, rightLabelWidth, copy.choiceSwitchHint)}
        {renderGroup(copy.streamTimingGroupTitle, timingRows, currentRow?.key ?? null, rightLabelWidth, copy.choiceSwitchHint)}
        {renderGroup(copy.streamPayloadGroupTitle, payloadRows, currentRow?.key ?? null, rightLabelWidth, copy.choiceSwitchHint)}
      </Box>
    </Box>
  );
}

function DefaultLayout({
  language,
  rows,
  activeKey,
}: {
  language: Language;
  rows: UiRow[];
  activeKey: string | null;
}): React.JSX.Element {
  const copy = getCopy(language);
  const labelWidth = Math.max(12, Math.min(22, ...rows.map((row) => visualWidth(row.label))));
  return <Box flexDirection="column">{renderAlignedRows(rows, activeKey, labelWidth, copy.choiceSwitchHint)}</Box>;
}

export function EditorPane({language, state, rows, validation, maxRows, width}: EditorPaneProps): React.JSX.Element {
  const copy = getCopy(language);
  const visibleRows = getWindowedRows(rows, state.rowIndex, maxRows);
  const currentRow = rows[state.rowIndex];
  const separator = "─".repeat(Math.max(24, width - 2));
  const groupInfo = activeGroupInfo(copy, state.section, currentRow);

  return (
    <Box flexDirection="column" flexGrow={1}>
      {state.section === "streams" ? (
        <StreamsLayout language={language} state={state} rows={rows} width={width} />
      ) : (
        <DefaultLayout language={language} rows={visibleRows} activeKey={currentRow?.key ?? null} />
      )}
      {state.section === "driver" ? (
        <Box marginTop={1}>
          <Text color="yellow">
            {copy.recommendedDriverLabel}: {copy.driverKindOptions[validation.recommendedDriverKind]}
          </Text>
        </Box>
      ) : null}
      <Box marginTop={1} flexDirection="column">
        <Text dimColor>{separator}</Text>
        <Text dimColor wrap="truncate-end">
          <Text bold>{groupInfo.title}</Text>: {groupInfo.description}
          {currentRow ? (
            <>
              <Text dimColor>  |  </Text>
              <Text bold>{currentRow.label}</Text>: {currentRow.description}
            </>
          ) : null}
        </Text>
      </Box>
    </Box>
  );
}
