import type { MetadataRoute } from "next";

import { SITE } from "@/content";

// Web app manifest (Next 16 file convention → manifest.webmanifest). Brand colors
// are the round-01 tokens inlined literally (#0c7a52 primary green, #ffffff canvas)
// — a manifest is static JSON, so the Tailwind theme vars cannot resolve here. The
// icons point at the two file-convention routes in this folder: the static
// `icon.svg` favicon and the generated `apple-icon` PNG.
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: SITE.name,
    short_name: SITE.name,
    description: SITE.description,
    start_url: "/",
    display: "standalone",
    background_color: "#ffffff",
    theme_color: "#0c7a52",
    icons: [
      { src: "/icon.svg", type: "image/svg+xml", sizes: "any" },
      { src: "/apple-icon", type: "image/png", sizes: "180x180" },
    ],
  };
}
