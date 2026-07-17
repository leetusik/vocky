// Shared content shapes for the typed @/content module. Pure types — no JSX, no
// runtime values. Later slices add page/section content types following this
// pattern.

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
