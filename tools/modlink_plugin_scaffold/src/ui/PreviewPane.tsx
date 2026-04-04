import React from "react";
import {Box, Text} from "ink";

import {getCopy, previewOrder} from "../lib/i18n.js";
import type {Language, PreviewBundle, PreviewTab} from "../lib/types.js";

type PreviewPaneProps = {
  language: Language;
  previewTab: PreviewTab;
  preview: PreviewBundle;
  maxLines: number;
};

function getPreviewText(preview: PreviewBundle, tab: PreviewTab): string {
  if (tab === "driver") {
    return preview.driver;
  }
  if (tab === "pyproject") {
    return preview.pyproject;
  }
  if (tab === "readme") {
    return preview.readme;
  }
  return preview.summary;
}

export function PreviewPane({language, previewTab, preview, maxLines}: PreviewPaneProps): React.JSX.Element {
  const copy = getCopy(language);
  const content = getPreviewText(preview, previewTab);
  const lines = content.split(/\r?\n/g);
  const visibleLines = lines.slice(0, maxLines);
  const truncated = lines.length > maxLines;

  return (
    <Box flexDirection="column" flexGrow={1} borderStyle="round" borderColor="cyan" paddingX={1}>
      <Text color="cyan">
        {copy.previewHeader}:{" "}
        {previewOrder
          .map((tab) => (tab === previewTab ? `[${copy.previewTabs[tab]}]` : copy.previewTabs[tab]))
          .join("  ")}
      </Text>
      <Box flexDirection="column" marginTop={1}>
        {visibleLines.map((line, index) => (
          <Text key={`${previewTab}-${index}`} wrap="truncate-end">
            {line}
          </Text>
        ))}
      </Box>
      {truncated ? (
        <Text dimColor>{copy.previewTruncated}</Text>
      ) : null}
    </Box>
  );
}
