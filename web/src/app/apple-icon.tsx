import { ImageResponse } from "next/og";

// Apple touch icon (Next 16 file convention → <link rel="apple-touch-icon">).
// Rebuilds the round-01 brand Mark (src/components/brand/mark.tsx) as an
// ImageResponse: the green rounded tile + three white rising bars, bottom-aligned
// on the same 32-unit grid scaled to 180px. LITERAL colors — the real Mark uses
// Tailwind `fill-*` utilities that resolve via CSS vars, which do not exist inside
// Satori/ImageResponse, so the brand tokens are inlined (#0c7a52 tile, #ffffff
// bars). No custom font is loaded (there is no text) — the default ImageResponse
// font is fine, and never blocks the build.

export const size = { width: 180, height: 180 };
export const contentType = "image/png";

export default function AppleIcon() {
  return new ImageResponse(
    <div
      style={{
        width: "100%",
        height: "100%",
        background: "#0c7a52",
        borderRadius: 50,
        display: "flex",
        alignItems: "flex-end",
        justifyContent: "center",
        gap: 17,
        paddingBottom: 45,
      }}
    >
      <div
        style={{
          width: 28,
          height: 45,
          borderRadius: 14,
          background: "#ffffff",
        }}
      />
      <div
        style={{
          width: 28,
          height: 73,
          borderRadius: 14,
          background: "#ffffff",
        }}
      />
      <div
        style={{
          width: 28,
          height: 101,
          borderRadius: 14,
          background: "#ffffff",
        }}
      />
    </div>,
    { ...size },
  );
}
