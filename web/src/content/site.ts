// Site-level brand + metadata. Single source for the wordmark and the
// title/description used by the Metadata API (wired in layout.tsx) and the
// metadata file-convention routes (robots/sitemap/manifest/OG). Chrome copy is
// English (root lang="en"); Korean *content* (feedback) renders via the
// Korean-capable font regardless. `url` reads the deploy env var and falls back
// to a local-dev origin; the production origin is now wired via the build-time
// public var NEXT_PUBLIC_APP_URL (injected as a Docker build arg in P6.S4/S5).
import type { SiteMeta } from "./types";

export const SITE: SiteMeta = {
  name: "vocky",
  title: "vocky",
  titleTemplate: "%s · vocky",
  // Marketing description (grounded in the landing hero copy), not the old
  // internal "tenant dashboard" line: it is the meta/OG/manifest description
  // every crawler and share card shows.
  description:
    "Capture the feedback your product is already getting. vocky turns explicit user reactions — likes, dislikes, comments — into structured signal you can search across every project.",
  url: process.env.NEXT_PUBLIC_APP_URL ?? "http://127.0.0.1:3030",
};
