import type { Metadata } from "next";

import { SITE } from "@/content";
import { jetbrainsMono, pretendard } from "@/lib/fonts";
import "./globals.css";

// Base metadata. `metadataBase` resolves canonical/OG URLs from SITE.url
// (NEXT_PUBLIC_APP_URL → local-dev origin fallback). The icon / apple-icon /
// opengraph-image / robots / sitemap / manifest file-convention routes now live
// beside this file (P6.S2); Next auto-injects og:image + twitter:image from
// opengraph-image.tsx, so only the textual OG/Twitter fields are set here.
export const metadata: Metadata = {
  metadataBase: new URL(SITE.url),
  title: {
    default: SITE.title,
    template: SITE.titleTemplate,
  },
  description: SITE.description,
  applicationName: SITE.name,
  openGraph: {
    title: SITE.title,
    description: SITE.description,
    siteName: SITE.name,
    url: SITE.url,
    type: "website",
    locale: "en_US",
  },
  twitter: {
    card: "summary_large_image",
    title: SITE.title,
    description: SITE.description,
  },
};

// Root layout. Chrome language is English (`lang="en"`); Korean *content*
// (feedback) still renders via the Korean-capable Pretendard font (Noto Sans KR
// fallback). The two self-hosted next/font variables are applied to <html> so
// font-sans / font-mono resolve everywhere; body defaults to font-sans on the
// canvas surface. The authenticated app shell + nav land in P4.S2 (they wrap the
// `(app)` route group, not this root layout).
export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${pretendard.variable} ${jetbrainsMono.variable}`}
    >
      <body className="flex min-h-dvh flex-col bg-canvas font-sans text-ink antialiased">
        {children}
      </body>
    </html>
  );
}
