import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

/**
 * Responsive card grid: always 1-up on mobile, scaling to 2–4 columns on larger
 * viewports. `cols` is a plain prop (not CVA) so the literal class strings stay
 * static for Tailwind's scanner.
 */
const colsClass: Record<2 | 3 | 4, string> = {
  2: "grid-cols-1 sm:grid-cols-2",
  3: "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3",
  4: "grid-cols-1 sm:grid-cols-2 lg:grid-cols-4",
};

export interface GridProps extends HTMLAttributes<HTMLDivElement> {
  /** Desktop column count. Mobile is always 1-up. Defaults to 3. */
  cols?: 2 | 3 | 4;
  /** Gap utility class. Defaults to `gap-4` (16px). */
  gap?: string;
}

export function Grid({
  className,
  cols = 3,
  gap = "gap-4",
  ...props
}: GridProps) {
  return (
    <div className={cn("grid", colsClass[cols], gap, className)} {...props} />
  );
}
