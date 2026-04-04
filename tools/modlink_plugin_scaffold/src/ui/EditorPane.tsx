import React from "react";
import {Box, Text} from "ink";

import {getCopy} from "../lib/i18n.js";
import type {Draft, Language, SectionId, ValidationResult} from "../lib/types.js";
import type {UiRow} from "./rows.js";

type EditorPaneProps = {
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

function rowDisplayValue(
  row: UiRow,
  choiceSwitchHint: string,
  editingKey: string | null,
  editingValue: string,
): string {
  const sourceValue = row.key === editingKey ? editingValue : row.value;
  const base = sourceValue || "<empty>";
  if (row.kind === "choice") {
    return `${base} ${choiceSwitchHint}`;
  }
  return base;
}

function activeGroupInfo(
  copy: ReturnType<typeof getCopy>,
  section: SectionId,
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

function renderAlignedRows(
  rows: UiRow[],
  activeKey: string | null,
  labelWidth: number,
  choiceSwitchHint: string,
  editingKey: string | null,
  editingValue: string,
): React.JSX.Element[] {
  return rows.map((row) => {
    const active = activeKey === row.key;
    const color = row.error ? "red" : active ? "cyan" : undefined;
    return (
      <Box key={row.key} flexDirection="column">
        <Box>
          <Box width={2}>
            <Text color={color}>{active ? ">" : " "}</Text>
          </Box>
          <Box width={labelWidth + 2}>
            <Text color={color} bold>
              {padToVisualWidth(row.label, labelWidth)}
            </Text>
          </Box>
          <Box flexGrow={1}>
            <Text color={color} wrap="truncate-end">
              {rowDisplayValue(row, choiceSwitchHint, editingKey, editingValue)}
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

function renderGroup(
  title: string,
  rows: UiRow[],
  activeKey: string | null,
  labelWidth: number,
  choiceSwitchHint: string,
  editingKey: string | null,
  editingValue: string,
): React.JSX.Element | null {
  if (rows.length === 0) {
    return null;
  }

  const groupLabelWidth = 10;

  return (
    <Box flexDirection="column" marginTop={1}>
      {rows.map((row, index) => {
        const active = activeKey === row.key;
        const color = row.error ? "red" : active ? "cyan" : undefined;
        return (
          <Box key={row.key} flexDirection="column">
            <Box>
              <Box width={groupLabelWidth}>
                <Text color={index === 0 ? "yellow" : undefined} bold={index === 0}>
                  {index === 0 ? title : ""}
                </Text>
              </Box>
              <Box width={2}>
                <Text color={color}>{active ? ">" : " "}</Text>
              </Box>
              <Box width={labelWidth + 2}>
                <Text color={color} bold>
                  {padToVisualWidth(row.label, labelWidth)}
                </Text>
              </Box>
              <Box flexGrow={1}>
                <Text color={color} wrap="truncate-end">
                  {rowDisplayValue(row, choiceSwitchHint, editingKey, editingValue)}
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

type StreamListPaneProps = {
  language: Language;
  listRows: UiRow[];
  actionRows: UiRow[];
  selectedStreamIndex: number;
  activeRowKey: string | null;
  width: number;
};

const StreamListPane = React.memo(function StreamListPane({
  language,
  listRows,
  actionRows,
  selectedStreamIndex,
  activeRowKey,
  width,
}: StreamListPaneProps): React.JSX.Element {
  const copy = getCopy(language);

  return (
    <Box width={width} borderStyle="round" borderColor="gray" paddingX={1} flexDirection="column">
      <Text color="yellow" bold>
        [{copy.streamListTitle}]
      </Text>
      <Text dimColor wrap="truncate-end">
        {copy.streamListDescription}
      </Text>
      <Box flexDirection="column">
        {listRows.map((row, index) => {
          const active = row.key === activeRowKey;
          const selected = index === selectedStreamIndex;
          const color = active ? "cyan" : selected ? "green" : undefined;
          const prefix = active ? ">" : selected ? "*" : " ";
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
          const active = row.key === activeRowKey;
          return (
            <Text key={row.key} color={active ? "cyan" : undefined}>
              {active ? ">" : " "} {row.label}
            </Text>
          );
        })}
      </Box>
    </Box>
  );
});

type StreamDetailsPaneProps = {
  language: Language;
  currentStream: Draft["streams"][number];
  basicRows: UiRow[];
  timingRows: UiRow[];
  payloadRows: UiRow[];
  activeRowKey: string | null;
  width: number;
  editingKey: string | null;
  editingValue: string;
};

const StreamDetailsPane = React.memo(function StreamDetailsPane({
  language,
  currentStream,
  basicRows,
  timingRows,
  payloadRows,
  activeRowKey,
  width,
  editingKey,
  editingValue,
}: StreamDetailsPaneProps): React.JSX.Element {
  const copy = getCopy(language);
  const rightLabelWidth = Math.max(
    14,
    Math.min(
      22,
      ...[...basicRows, ...timingRows, ...payloadRows].map((row) => visualWidth(row.label)),
    ),
  );

  return (
    <Box width={width} borderStyle="round" borderColor="gray" paddingX={1} flexDirection="column">
      <Text wrap="truncate-end">
        <Text color="yellow" bold>
          [{copy.streamDetailsTitle}]
        </Text>
        <Text dimColor>  {currentStream.displayName || currentStream.modality}</Text>
        <Text dimColor> · {copy.payloadOptions[currentStream.payloadType]}</Text>
      </Text>
      {renderGroup(copy.streamBasicGroupTitle, basicRows, activeRowKey, rightLabelWidth, copy.choiceSwitchHint, editingKey, editingValue)}
      {renderGroup(copy.streamTimingGroupTitle, timingRows, activeRowKey, rightLabelWidth, copy.choiceSwitchHint, editingKey, editingValue)}
      {renderGroup(copy.streamPayloadGroupTitle, payloadRows, activeRowKey, rightLabelWidth, copy.choiceSwitchHint, editingKey, editingValue)}
    </Box>
  );
});

type DefaultLayoutProps = {
  language: Language;
  rows: UiRow[];
  activeKey: string | null;
  editingKey: string | null;
  editingValue: string;
};

const DefaultLayout = React.memo(function DefaultLayout({
  language,
  rows,
  activeKey,
  editingKey,
  editingValue,
}: DefaultLayoutProps): React.JSX.Element {
  const copy = getCopy(language);
  const labelWidth = Math.max(12, Math.min(22, ...rows.map((row) => visualWidth(row.label))));
  return (
    <Box flexDirection="column">
      {renderAlignedRows(rows, activeKey, labelWidth, copy.choiceSwitchHint, editingKey, editingValue)}
    </Box>
  );
});

export const EditorPane = React.memo(function EditorPane({
  language,
  section,
  draft,
  rowIndex,
  rows,
  validation,
  maxRows,
  width,
  editingKey,
  editingValue,
}: EditorPaneProps): React.JSX.Element {
  const copy = getCopy(language);
  const visibleRows = getWindowedRows(rows, rowIndex, maxRows);
  const currentRow = rows[rowIndex];
  const separator = "─".repeat(Math.max(24, width - 2));
  const groupInfo = activeGroupInfo(copy, section, currentRow);

  if (section === "streams") {
    const gap = 2;
    const leftWidth = Math.max(26, Math.min(32, Math.floor(width * 0.3)));
    const rightWidth = Math.max(40, width - leftWidth - gap);
    const listRows = rows.filter((row) => row.zone === "stream-list");
    const actionRows = rows.filter((row) => row.zone === "stream-action");
    const basicRows = rows.filter((row) => row.zone === "stream-basic");
    const timingRows = rows.filter((row) => row.zone === "stream-timing");
    const payloadRows = rows.filter((row) => row.zone === "stream-payload");

    return (
      <Box flexDirection="column" flexGrow={1}>
        <Box flexGrow={1}>
          <StreamListPane
            language={language}
            listRows={listRows}
            actionRows={actionRows}
            selectedStreamIndex={draft.selectedStreamIndex}
            activeRowKey={currentRow?.key ?? null}
            width={leftWidth}
          />
          <Box width={gap} />
          <StreamDetailsPane
            language={language}
            currentStream={draft.streams[draft.selectedStreamIndex]}
            basicRows={basicRows}
            timingRows={timingRows}
            payloadRows={payloadRows}
            activeRowKey={currentRow?.key ?? null}
            width={rightWidth}
            editingKey={editingKey}
            editingValue={editingValue}
          />
        </Box>
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

  return (
    <Box flexDirection="column" flexGrow={1}>
      <DefaultLayout
        language={language}
        rows={visibleRows}
        activeKey={currentRow?.key ?? null}
        editingKey={editingKey}
        editingValue={editingValue}
      />
      {section === "driver" ? (
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
});
