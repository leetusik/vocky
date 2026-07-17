import type { SVGProps } from "react";

import { cn } from "@/lib/utils";

/**
 * The vocky brand mark (round 01, build-prompt §7.1): three rising rounded bars —
 * a waveform / capture-volume motif — in white on a green (`--color-green`)
 * rounded-square tile. Simple geometry, no illustration; fully static (no motion,
 * so reduced-motion-safe by construction). The first real vocky brand asset,
 * reused by the app shell, the auth card, the net-new states, and the landing.
 *
 * `size` is the tile edge in px: 32 in the chrome (default), 52 for the hero /
 * empty states. The tile fill is a prop (`tileClassName`, default `fill-green`)
 * so a future danger-tinted variant (S5's `error` / `global-error`) can restyle
 * the tile without forking the geometry — that variant is left for S5 to add, not
 * built speculatively here.
 *
 * Decorative by default (`aria-hidden`): a Wordmark or a heading always carries
 * the accessible name beside it. Pass `aria-hidden={false}` + `aria-label` to give
 * a standalone mark its own name.
 */
export interface MarkProps extends Omit<
  SVGProps<SVGSVGElement>,
  "width" | "height"
> {
  /** Tile edge in px. 32 = chrome (default), 52 = hero / empty states. */
  size?: number;
  /** Tile fill utility; `fill-green` by default. Lets S5 tint it (e.g. danger). */
  tileClassName?: string;
}

export function Mark({
  size = 32,
  tileClassName = "fill-green",
  className,
  ...props
}: MarkProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      aria-hidden="true"
      className={cn("shrink-0", className)}
      {...props}
    >
      <rect width={32} height={32} rx={9} className={tileClassName} />
      <rect
        x={5.5}
        y={16}
        width={5}
        height={8}
        rx={2.5}
        className="fill-white"
      />
      <rect
        x={13.5}
        y={11}
        width={5}
        height={13}
        rx={2.5}
        className="fill-white"
      />
      <rect
        x={21.5}
        y={6}
        width={5}
        height={18}
        rx={2.5}
        className="fill-white"
      />
    </svg>
  );
}
