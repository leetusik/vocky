import type { MetadataRoute } from "next";

import { SITE } from "@/content";

// robots.txt (Next 16 file convention). The public landing `/` is crawlable; the
// authenticated app and the BFF proxy routes are not — they need a session and
// only ever 404/redirect for a crawler anyway. `sitemap`/`host` derive from
// SITE.url (NEXT_PUBLIC_APP_URL → local-dev fallback), so they follow the real
// production origin without a hardcoded URL.
export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: ["/dashboard", "/projects/", "/feedback", "/api/"],
    },
    sitemap: `${SITE.url}/sitemap.xml`,
    host: SITE.url,
  };
}
