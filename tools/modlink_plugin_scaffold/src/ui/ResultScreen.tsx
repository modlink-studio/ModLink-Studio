import React from "react";
import {Box, Text} from "ink";

import {getCopy} from "../lib/i18n.js";
import type {GeneratedProject, Language} from "../lib/types.js";

type ResultScreenProps = {
  language: Language;
  result: GeneratedProject;
  width?: number;
  height?: number;
};

export function ResultScreen({language, result, width, height}: ResultScreenProps): React.JSX.Element {
  const copy = getCopy(language);

  return (
    <Box width={width} height={height} justifyContent="center" alignItems="center">
      <Box flexDirection="column" borderStyle="round" borderColor="green" padding={1} width={Math.max(48, Math.min((width ?? 80) - 4, 84))}>
        <Text color="green" bold>
          {copy.completionTitle}
        </Text>
        <Text wrap="truncate-middle">{result.projectDir}</Text>
        <Box flexDirection="column" marginTop={1}>
          <Text color="yellow">{copy.commandsLabel}</Text>
          <Text>install: {result.commands.install}</Text>
          <Text>test: {result.commands.test}</Text>
          <Text>run: {result.commands.runHost}</Text>
          <Text>entry-points: {result.commands.checkEntryPoints}</Text>
        </Box>
        <Text dimColor>{copy.completionHint}</Text>
      </Box>
    </Box>
  );
}
