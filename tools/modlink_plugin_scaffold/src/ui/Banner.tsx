import React from "react";
import {Box, Text} from "ink";

import {getCopy} from "../lib/i18n.js";
import type {Language, SummaryViewModel} from "../lib/types.js";

type BannerProps = {
  language: Language;
  summary: SummaryViewModel;
  width: number;
};

function clampLine(value: string, width: number): string {
  const safeWidth = Math.max(10, width);
  if (value.length <= safeWidth) {
    return value;
  }
  return `${value.slice(0, Math.max(0, safeWidth - 1))}…`;
}

function MetricLine({
  items,
  width,
}: {
  items: Array<{label: string; value: string}>;
  width: number;
}): React.JSX.Element {
  const gap = 2;
  const cellWidth = Math.max(16, Math.floor((width - gap * Math.max(0, items.length - 1)) / Math.max(1, items.length)));

  return (
    <Box>
      {items.map((item, index) => (
        <React.Fragment key={item.label}>
          <Box width={cellWidth}>
            <Text wrap="truncate-end">
              <Text bold>{item.label}</Text> {clampLine(item.value, Math.max(8, cellWidth - item.label.length - 1))}
            </Text>
          </Box>
          {index < items.length - 1 ? <Box width={gap} /> : null}
        </React.Fragment>
      ))}
    </Box>
  );
}

export const Banner = React.memo(function Banner({language, summary, width}: BannerProps): React.JSX.Element {
  const copy = getCopy(language);
  const boxWidth = Math.max(24, width);
  const contentWidth = Math.max(20, boxWidth - 4);

  if (summary.kind === "invalid") {
    return (
      <Box width={boxWidth} borderStyle="round" borderColor="red" paddingX={1} flexDirection="column">
        <Text bold dimColor>
          [{summary.title}]
        </Text>
        <Text wrap="truncate-end">{summary.message}</Text>
        {summary.errors.length > 0 ? (
          <Text wrap="truncate-end">
            <Text bold>{copy.validationErrorsHeader}:</Text> {clampLine(summary.errors.join(" | "), contentWidth - 8)}
          </Text>
        ) : null}
      </Box>
    );
  }

  const metricByLabel = new Map(summary.metrics.map((metric) => [metric.label, metric.value]));

  return (
    <Box width={boxWidth} borderStyle="round" borderColor="green" paddingX={1} flexDirection="column">
      <Text wrap="truncate-end">
        <Text bold dimColor>[{summary.title}]</Text>
        <Text color="green" bold>  {summary.hero.displayName}</Text>
        <Text dimColor>  {copy.pluginNameLabel} {summary.hero.pluginName}</Text>
      </Text>
      <MetricLine
        width={contentWidth}
        items={[
          {label: copy.deviceIdLabel, value: metricByLabel.get(copy.deviceIdLabel) ?? summary.hero.deviceId},
          {label: copy.providersLabel, value: metricByLabel.get(copy.providersLabel) ?? ""},
        ]}
      />
      <MetricLine
        width={contentWidth}
        items={[
          {label: copy.driverKindLabel, value: metricByLabel.get(copy.driverKindLabel) ?? ""},
          {label: copy.dataArrivalLabel, value: metricByLabel.get(copy.dataArrivalLabel) ?? ""},
          {label: copy.streamCountLabel, value: metricByLabel.get(copy.streamCountLabel) ?? ""},
        ]}
      />
    </Box>
  );
});
