import { Box, Text } from "ink";
import React from "react";

import { getCopy } from "../lib/i18n.js";
import type { Language } from "../lib/types.js";

type FooterStatusProps = {
  language: Language;
  cwd: string;
  statusMessage: string | null;
  editingValue: string;
  isEditing: boolean;
};

export const FooterStatus = React.memo(function FooterStatus({
  language,
  cwd,
  statusMessage,
  editingValue,
  isEditing,
}: FooterStatusProps): React.JSX.Element {
  const copy = getCopy(language);

  return (
    <Box flexDirection="column" height={2} justifyContent="center">
      {isEditing ? (
        <>
          <Text color="yellow" wrap="truncate-end">
            {copy.editingLabel}&gt; {editingValue}
            <Text color="white">█</Text>
          </Text>
          <Text dimColor wrap="truncate-end">
            {copy.controlsLabel}: {copy.footerEditHint}
          </Text>
        </>
      ) : (
        <>
          <Text dimColor wrap="truncate-middle">
            {copy.locationLabel}: {statusMessage ?? cwd}
          </Text>
          <Text dimColor wrap="truncate-end">
            {copy.controlsLabel}: {copy.footerIdleHint}
          </Text>
        </>
      )}
    </Box>
  );
});
