import type { Metadata } from "next";

import { SITE } from "@/content";
import { jetbrainsMono, pretendard } from "@/lib/fonts";
import "./globals.css";

// Base metadata. `metadataBase` resolves canonical/OG URLs from SITE.url
// (NEXT_PUBLIC_APP_URL → local-dev origin fallback). Icon / OG / robots /
// sitemap file-convention routes are a P6 concern, not this scaffold slice.
export const metadata: Metadata = {
  metadataBase: new URL(SITE.url),
  title: {
    default: SITE.title,
    template: SITE.titleTemplate,
  },
  description: SITE.description,
  applicationName: SITE.name,
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
