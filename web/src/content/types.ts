// Shared content shapes for the typed @/content module. Pure types — no JSX, no
// runtime values. Later slices add page/section content types following this
// pattern. SectionId is re-exported here so consumers can pull every content
// type from one place.
import type { SectionId } from "./section-ids";

export type { SectionId };

export interface NavLink {
  label: string;
  href: string;
  /** For in-page section links, the section id a scroll-spy would highlight. */
  sectionId?: SectionId;
}

export interface Cta {
  label: string;
  href: string;
}

export interface SiteMeta {
  /** Brand wordmark, e.g. "vocky" */
  name: string;
  /** Default document title */
  title: string;
  /** Template for per-page titles, e.g. "%s · vocky" */
  titleTemplate: string;
  /** Meta description */
  description: string;
  /** Absolute site origin used for metadataBase / canonical / OG */
  url: string;
}
