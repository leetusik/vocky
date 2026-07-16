import { JetBrains_Mono, Noto_Sans_KR } from "next/font/google";

/**
 * Fonts via `next/font/google` (P4.S1 placeholder set). Build-time self-hosted
 * (no third-party request at runtime, CSP-safe), no vendored woff2 binaries, no
 * subset toolchain. Each exposes a CSS variable consumed by the `@theme` font
 * families in `globals.css`:
 *   --font-noto-sans-kr → font-sans  (Korean-capable; the app renders Korean feedback)
 *   --font-jetbrains-mono → font-mono
 *
 * These are placeholders, cleanly swappable to the vocky brand faces (e.g.
 * Pretendard) at the P6 design gate — the `@theme` token NAMES (`--font-sans` /
 * `--font-mono`) stay put, so only the wiring here changes. The `latin` subset
 * is preloaded; Korean glyphs are self-hosted by next/font and served on demand.
 */

export const notoSansKr = Noto_Sans_KR({
  subsets: ["latin"],
  weight: ["400", "500", "700"],
  display: "swap",
  variable: "--font-noto-sans-kr",
});

export const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "700"],
  display: "swap",
  variable: "--font-jetbrains-mono",
});
