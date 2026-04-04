import React from "react";
import {Box, Text} from "ink";

import {getCopy} from "../lib/i18n.js";
import type {Language, ModalFocus} from "../lib/types.js";

type OverwriteDialogProps = {
  language: Language;
  projectPath: string;
  focus: ModalFocus;
};

export function OverwriteDialog({language, projectPath, focus}: OverwriteDialogProps): React.JSX.Element {
  const copy = getCopy(language);

  return (
    <Box flexDirection="column" borderStyle="round" borderColor="yellow" padding={1}>
      <Text color="yellow" bold>
        {copy.confirmOverwriteTitle}
      </Text>
      <Text>{copy.confirmOverwriteBody}</Text>
      <Text>{projectPath}</Text>
      <Box marginTop={1}>
        <Text color={focus === "cancel" ? "cyan" : undefined}>[{copy.confirmOverwriteCancel}]</Text>
        <Text> </Text>
        <Text color={focus === "overwrite" ? "red" : undefined}>[{copy.confirmOverwriteConfirm}]</Text>
      </Box>
    </Box>
  );
}
