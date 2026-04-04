import { Box, Text } from "ink";
import React from "react";

import { getCopy } from "../lib/i18n.js";
import type { Language, ModalFocus } from "../lib/types.js";

type OverwriteDialogProps = {
  language: Language;
  projectPath: string;
  focus: ModalFocus;
  width?: number;
  height?: number;
};

export const OverwriteDialog = React.memo(function OverwriteDialog({
  language,
  projectPath,
  focus,
  width,
  height,
}: OverwriteDialogProps): React.JSX.Element {
  const copy = getCopy(language);

  return (
    <Box width={width} height={height} justifyContent="center" alignItems="center">
      <Box
        flexDirection="column"
        borderStyle="round"
        borderColor="yellow"
        padding={1}
        width={Math.max(40, Math.min((width ?? 60) - 4, 72))}
      >
        <Text color="yellow" bold>
          {copy.confirmOverwriteTitle}
        </Text>
        <Text>{copy.confirmOverwriteBody}</Text>
        <Text wrap="truncate-middle">{projectPath}</Text>
        <Box marginTop={1}>
          <Text color={focus === "cancel" ? "cyan" : undefined}>
            [{copy.confirmOverwriteCancel}]
          </Text>
          <Text> </Text>
          <Text color={focus === "overwrite" ? "red" : undefined}>
            [{copy.confirmOverwriteConfirm}]
          </Text>
        </Box>
      </Box>
    </Box>
  );
});
