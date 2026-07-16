// Site-level brand + metadata. Single source for the wordmark and the
// title/description used by the Metadata API (wired in layout.tsx). Chrome copy
// is English (root lang="en"); Korean *content* (feedback) renders via the
// Korean-capable font regardless. `url` reads the deploy env var and falls back
// to a local-dev origin (production origin is a P6 deploy concern).
import type { SiteMeta } from "./types";

export const SITE: SiteMeta = {
  name: "vocky",
  title: "vocky",
  titleTemplate: "%s · vocky",
  description:
    "vocky — the tenant dashboard for your projects, credentials, and feedback.",
  url: process.env.NEXT_PUBLIC_APP_URL ?? "http://127.0.0.1:3030",
};
