import React from "react";
import {Box, Text} from "ink";

type AppShellProps = {
  width: number;
  height: number;
  title: string;
  status: string;
  statusColor: string;
  tabs: React.ReactNode;
  description: string;
  banner: React.ReactNode;
  content: React.ReactNode;
  footer: React.ReactNode;
};

export function AppShell({
  width,
  height,
  title,
  status,
  statusColor,
  tabs,
  description,
  banner,
  content,
  footer,
}: AppShellProps): React.JSX.Element {
  return (
    <Box width={width} height={height} borderStyle="round" borderColor="green" flexDirection="column" paddingX={1}>
      <Box justifyContent="space-between">
        <Text bold color="green">
          {title}
        </Text>
        <Text color={statusColor}>{status}</Text>
      </Box>
      {tabs}
      {description ? (
        <Text dimColor wrap="truncate-end">
          {description}
        </Text>
      ) : null}
      {banner}
      <Box flexGrow={1} borderTop borderBottom borderColor="gray">
        <Box flexGrow={1} paddingRight={1}>
          {content}
        </Box>
      </Box>
      {footer}
    </Box>
  );
}
