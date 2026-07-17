// Single source of truth for in-page anchor ids. Every <Section id> and every
// landing nav link derives from this map so links and section targets never
// drift. Keys are camelCase symbols; values are the kebab-case ids used in the
// DOM and in `#...` hrefs.
//
// `features` / `how` / `pricing` are the public landing's real section anchors
// (P9.S6, build-prompt §4.12) — the landing nav scrolls to them.
export const SECTION_IDS = {
  // Public landing anchors (P9.S6).
  features: "features",
  how: "how",
  pricing: "pricing",
} as const;

export type SectionId = (typeof SECTION_IDS)[keyof typeof SECTION_IDS];
