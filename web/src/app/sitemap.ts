import type { MetadataRoute } from "next";

import { SITE } from "@/content";

// sitemap.xml (Next 16 file convention). The landing `/` is the only public,
// crawlable page — everything else lives behind auth. The absolute URL derives
// from SITE.url (the real production origin via NEXT_PUBLIC_APP_URL).
export default function sitemap(): MetadataRoute.Sitemap {
  return [
    {
      url: SITE.url,
      lastModified: new Date(),
      changeFrequency: "monthly",
      priority: 1,
    },
  ];
}
