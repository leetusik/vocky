import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

/**
 * The vocky wordmark (round 01, build-prompt §7.1): lowercase "vocky" in the
 * brand face at weight 800 with a tight `-1px` tracking. Paired with the Mark in
 * the chrome and on the landing; carries the accessible brand name (the Mark is
 * decorative). The `tone` prop swaps the ink between light surfaces (`text-ink`,
 * default — the app shell / light bands) and dark ones (white — the landing's
 * forest/ink bands). Size is `text-[18px]` by default; the landing hero scales it
 * up via `className`.
 */
export interface WordmarkProps extends HTMLAttributes<HTMLSpanElement> {
  /** `light` → `text-ink` (default, app chrome); `dark` → white (dark bands). */
  tone?: "light" | "dark";
}

export function Wordmark({
  tone = "light",
  className,
  ...props
}: WordmarkProps) {
  return (
    <span
      className={cn(
        "font-en text-[18px] leading-none font-extrabold tracking-[-1px] lowercase",
        tone === "dark" ? "text-white" : "text-ink",
        className,
      )}
      {...props}
    >
      vocky
    </span>
  );
}
