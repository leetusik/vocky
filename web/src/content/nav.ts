// Header navigation + CTAs (placeholder set for the S1 preview). Real app nav —
// dashboard / projects / feedback — lands with the authenticated app shell in
// P4.S2. Section links are built from SECTION_IDS so they never drift.
import { SECTION_IDS } from "./section-ids";
import type { Cta, NavLink, SectionId } from "./types";

const section = (id: SectionId, label: string): NavLink => ({
  label,
  href: `#${id}`,
  sectionId: id,
});

export const NAV_LINKS: NavLink[] = [
  section(SECTION_IDS.overview, "Overview"),
  section(SECTION_IDS.primitives, "Primitives"),
];

// Skip-to-content link target (WCAG 2.4.1). Points at the document `<main>`
// landmark so keyboard/AT users can jump past the header.
export const SKIP_TO_CONTENT: Cta = {
  label: "Skip to content",
  href: "#main-content",
};
