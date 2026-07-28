import type { HTMLAttributes, ReactNode } from "react";

import { cn } from "@/lib/utils";

/**
 * Trap — a known, non-fatal hazard (round 02, build-prompt §3.2).
 *
 * A plain `<aside>` in the caution family, which shipped with round 01 and had no
 * consumer until now. It marks something that WILL bite you if you skip it (the
 * Codex `workspace-write` sandbox denying outbound network, say) — a hazard, not
 * an error that just happened.
 *
 * DELIBERATELY NOT AN ALERT — do not "fix" this into one. No `role="alert"`, no
 * `aria-live`, no icon component, no emoji (§3.2, §9). Nothing in this round may
 * interrupt a screen reader on page load, and a trap is static prose that is true
 * whether or not the reader is looking at it. The word "trap" is in the label, so
 * colour is never the sole signal.
 *
 * The 7px diamond marker is a real `aria-hidden` `<span>` rather than the spec's
 * `::before`: pseudo-element geometry is not expressible in utilities here, and a
 * rotated square is the designed mark — never substitute a bullet or an icon.
 *
 * Inline `<code>` inside `children` is styled by the body's descendant utilities
 * (§3.2: mono 12.5px on `rgba(14,26,22,.055)`, radius 4, `1px 5px`), so consumers
 * write plain `<code>` and cannot drift from the treatment.
 */
export interface TrapProps extends HTMLAttributes<HTMLElement> {
  /** Uppercase mono label, e.g. "Known trap · Codex only". */
  label: ReactNode;
  /** Body prose; inline `<code>` is styled for you. */
  children: ReactNode;
}

export function Trap({ className, label, children, ...props }: TrapProps) {
  return (
    <aside
      className={cn(
        "rounded-lg border border-hairline-caution bg-surface-caution px-4 py-3.5",
        className,
      )}
      {...props}
    >
      <p className="flex items-center gap-2 font-mono text-micro text-caution-deep uppercase">
        <span
          aria-hidden="true"
          className="size-[7px] shrink-0 rotate-45 bg-caution"
        />
        {label}
      </p>
      <div className="mt-2 text-[13.5px] leading-[1.6] text-slate [&_code]:rounded-xs [&_code]:bg-[rgba(14,26,22,0.055)] [&_code]:px-[5px] [&_code]:py-px [&_code]:font-mono [&_code]:text-[12.5px]">
        {children}
      </div>
    </aside>
  );
}
