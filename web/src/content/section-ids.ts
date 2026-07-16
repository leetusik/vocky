// Single source of truth for in-page anchor ids. Every nav link and every
// <Section id> derives from this map so links and section targets never drift.
// Keys are camelCase symbols; values are the kebab-case ids used in the DOM and
// in `#...` hrefs. These are placeholders for the S1 design-system preview;
// later slices add the real app section ids.
export const SECTION_IDS = {
  overview: "overview",
  primitives: "primitives",
} as const;

export type SectionId = (typeof SECTION_IDS)[keyof typeof SECTION_IDS];
