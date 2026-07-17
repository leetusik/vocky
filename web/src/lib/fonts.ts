import localFont from "next/font/local";
import { JetBrains_Mono } from "next/font/google";

/**
 * Brand faces for the vocky design system (applied by P9 from the round 01
 * design-gate signoff — see `build-prompt.md §3`).
 *
 *   --font-pretendard   → font-sans  (Pretendard, Korean-capable; the app
 *                                      renders Korean feedback)
 *   --font-jetbrains-mono → font-mono (JetBrains Mono, data/code)
 *
 * Both are build-time self-hosted (no third-party request at runtime, CSP-safe).
 *
 * Pretendard is not on Google Fonts, so it is vendored as a single variable
 * woff2 (`./fonts/PretendardVariable.woff2`, one file covering weights 400–800)
 * loaded via `next/font/local` — self-contained, no runtime dependency, and in
 * line with the app's existing self-host philosophy. The CSS variable name is
 * `--font-pretendard`; the `@theme --font-sans` chain in `globals.css` leads
 * with it and keeps a Korean-capable fallback (Noto Sans KR).
 */

export const pretendard = localFont({
  src: "./fonts/PretendardVariable.woff2",
  display: "swap",
  weight: "400 800",
  variable: "--font-pretendard",
  fallback: ["Pretendard", "Noto Sans KR", "system-ui", "sans-serif"],
});

export const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "700"],
  display: "swap",
  variable: "--font-jetbrains-mono",
});
