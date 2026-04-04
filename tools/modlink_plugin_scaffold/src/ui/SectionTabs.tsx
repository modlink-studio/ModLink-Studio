import { Box, Text } from "ink";
import React from "react";
import { getCopy, sectionOrder } from "../lib/i18n.js";
import type { Language, SectionId } from "../lib/types.js";

type SectionTabsProps = {
  language: Language;
  currentSection: SectionId;
};

export const SectionTabs = React.memo(function SectionTabs({
  language,
  currentSection,
}: SectionTabsProps): React.JSX.Element {
  const copy = getCopy(language);

  return (
    <Box>
      {sectionOrder.map((section) => (
        <Box key={section} flexGrow={1} justifyContent="center">
          <Text
            color={section === currentSection ? "cyan" : "gray"}
            bold={section === currentSection}
          >
            {section === currentSection ? `[${copy.sections[section]}]` : copy.sections[section]}
          </Text>
        </Box>
      ))}
    </Box>
  );
});
