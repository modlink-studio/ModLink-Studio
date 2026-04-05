import { Box, Text } from "ink";
import React from "react";

import { getCopy } from "../lib/i18n.js";
import type { Language, SummaryViewModel } from "../lib/types.js";

type BannerProps = {
  language: Language;
  summary: SummaryViewModel;
  width: number;
};

type MetricCell = {
  label: string;
  value: string;
};

function clampLine(value: string, width: number): string {
  const safeWidth = Math.max(10, width);
  if (value.length <= safeWidth) {
    return value;
  }
  return `${value.slice(0, Math.max(0, safeWidth - 1))}…`;
}

function MetricRow({
  left,
  right,
  width,
}: {
  left: MetricCell;
  right?: MetricCell;
  width: number;
}): React.JSX.Element {
  const gap = 2;
  const cellWidth = Math.max(18, Math.floor((width - gap) / 2));

  return (
    <Box>
      <Box width={cellWidth}>
        <Text wrap="truncate-end">
          <Text bold>{left.label}:</Text> {left.value}
        </Text>
      </Box>
      <Box width={gap} />
      <Box width={cellWidth}>
        {right ? (
          <Text wrap="truncate-end">
            <Text bold>{right.label}:</Text> {right.value}
          </Text>
        ) : null}
      </Box>
    </Box>
  );
}

export const Banner = React.memo(function Banner({
  language,
  summary,
  width,
}: BannerProps): React.JSX.Element {
  const copy = getCopy(language);
  const boxWidth = Math.max(24, width);
  const contentWidth = Math.max(20, boxWidth - 4);

  if (summary.kind === "invalid") {
    const visibleErrors = summary.errors.slice(0, 2);
    const remainingErrors = summary.errors.length - visibleErrors.length;

    return (
      <Box
        width={boxWidth}
        borderStyle="round"
        borderColor="red"
        paddingX={1}
        flexDirection="column"
      >
        <Text bold dimColor>
          [{summary.title}]
        </Text>
        <Text wrap="truncate-end">{summary.message}</Text>
        <Text bold color="red">
          {copy.validationErrorsHeader}:
        </Text>
        {visibleErrors.map((error) => (
          <Text key={error} color="red" wrap="truncate-end">
            - {clampLine(error, contentWidth - 2)}
          </Text>
        ))}
        {remainingErrors > 0 ? <Text dimColor>+ {remainingErrors} more</Text> : null}
      </Box>
    );
  }

  const metricByLabel = new Map(summary.metrics.map((metric) => [metric.label, metric.value]));

  return (
    <Box
      width={boxWidth}
      borderStyle="round"
      borderColor="green"
      paddingX={1}
      flexDirection="column"
    >
      <Text bold dimColor>
        [{summary.title}]
      </Text>
      <Text color="green" bold wrap="truncate-end">
        {summary.hero.displayName}
      </Text>
      <Text dimColor wrap="truncate-end">
        {copy.pluginNameLabel} {summary.hero.pluginName}
      </Text>
      <MetricRow
        width={contentWidth}
        left={{
          label: copy.deviceIdLabel,
          value: metricByLabel.get(copy.deviceIdLabel) ?? summary.hero.deviceId,
        }}
        right={{
          label: copy.providersLabel,
          value: metricByLabel.get(copy.providersLabel) ?? "",
        }}
      />
      <MetricRow
        width={contentWidth}
        left={{
          label: copy.driverKindLabel,
          value: metricByLabel.get(copy.driverKindLabel) ?? "",
        }}
        right={{
          label: copy.dataArrivalLabel,
          value: metricByLabel.get(copy.dataArrivalLabel) ?? "",
        }}
      />
      <MetricRow
        width={contentWidth}
        left={{
          label: copy.streamCountLabel,
          value: metricByLabel.get(copy.streamCountLabel) ?? "",
        }}
      />
    </Box>
  );
});
