// Single source of truth for in-page anchor ids. Every nav link and every
// <Section id> derives from this map so links and section targets never drift.
// Keys are camelCase symbols; values are the kebab-case ids used in the DOM and
// in `#...` hrefs.
//
// `features` / `how` / `pricing` are the public landing's real section anchors
// (P9.S6, build-prompt §4.12) — the landing nav scrolls to them. `overview` /
// `primitives` are dead leftovers from the retired S1 design-system preview,
// kept only because `content/nav.ts` still references them; P9.S7 retires both
// nav.ts and these two ids together.
export const SECTION_IDS = {
  // Public landing anchors (P9.S6).
  features: "features",
  how: "how",
  pricing: "pricing",
  // Dead — S1 preview leftovers, still referenced by nav.ts. Retired by P9.S7.
  overview: "overview",
  primitives: "primitives",
} as const;

export type SectionId = (typeof SECTION_IDS)[keyof typeof SECTION_IDS];
