import { ImageResponse } from "next/og";

import { LANDING, SITE } from "@/content";

// Open Graph / Twitter card (Next 16 file convention → auto-injected og:image +
// twitter:image, so layout.tsx does not set them by hand). A minimal, brand-faithful
// card assembled from the EXISTING round-01 brand — the Mark geometry + the "vocky"
// wordmark on the forest brand background — plus one line of real landing copy
// (LANDING.hero.headline, imported from @/content, never re-typed). No invented
// illustration: that would be a separate design gate (phase.md Constraints).
//
// LITERAL colors — Satori/ImageResponse cannot resolve the Tailwind `fill-*` /
// theme CSS vars, so the brand tokens are inlined: #14231e (forest bg), #0c7a52
// (green tile), #ffffff (bars + text). No custom font is loaded (Pretendard is a
// variable woff2 that Satori may reject); the default ImageResponse font keeps the
// build robust.

export const alt = `${SITE.name} — ${LANDING.hero.headline}`;
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OpengraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          background: "#14231e",
          padding: "96px 100px",
        }}
      >
        {/* Mark + wordmark lockup */}
        <div style={{ display: "flex", alignItems: "center", gap: 28 }}>
          <div
            style={{
              width: 96,
              height: 96,
              background: "#0c7a52",
              borderRadius: 27,
              display: "flex",
              alignItems: "flex-end",
              justifyContent: "center",
              gap: 9,
              paddingBottom: 24,
            }}
          >
            <div style={{ width: 15, height: 24, borderRadius: 7, background: "#ffffff" }} />
            <div style={{ width: 15, height: 39, borderRadius: 7, background: "#ffffff" }} />
            <div style={{ width: 15, height: 54, borderRadius: 7, background: "#ffffff" }} />
          </div>
          <div
            style={{
              fontSize: 76,
              fontWeight: 800,
              letterSpacing: -2,
              color: "#ffffff",
            }}
          >
            {SITE.name}
          </div>
        </div>

        {/* One line of real landing copy */}
        <div
          style={{
            marginTop: 56,
            fontSize: 56,
            fontWeight: 600,
            lineHeight: 1.15,
            letterSpacing: -1,
            maxWidth: 900,
            color: "#ffffff",
          }}
        >
          {LANDING.hero.headline}
        </div>
      </div>
    ),
    { ...size },
  );
}
