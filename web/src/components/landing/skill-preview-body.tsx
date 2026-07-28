"use client";

import { type ReactNode, useState } from "react";

import { useIsHydrated } from "@/lib/use-is-hydrated";
import { cn } from "@/lib/utils";

import { SKILL_CONTROL_CLASS, SKILL_FILE_DOM_ID } from "./skill-shared";

/**
 * SkillPreviewBody — the preview pane's scroller + fade + footer (round 02,
 * build-prompt §3.4 / §7 / §8). The ONLY client code in the pane.
 *
 * THE FLOOR THIS FILE EXISTS TO PROTECT (build-prompt §8, `P11.DECOMP2`
 * correction 7): **the whole file is always in the server HTML.** §3.4's
 * "collapsed shows the first 22 lines of the body" reads like a truncation; it
 * is not one. §8 is explicit — the pane is "server-rendered with the file
 * already in the HTML… so all <n> lines are readable without JS" — and the
 * design's own `result.md` §6.5 settles it: "a scroller (rather than a hard
 * clip) means a no-JS visitor can still read all <n> lines."
 *
 * So "collapsed" is a VISUAL WINDOW, never a content cut:
 *   - collapsed  → 300px (narrow) / 380px scroller + the bottom fade
 *   - expanded   → 480px / 640px, fade gone — still a scroller, never unbounded
 *   - the text   → identical in both, and identical without JS
 *
 * That is why the body arrives as `children`-style ReactNode props rendered on
 * the SERVER (`skill-preview.tsx`) and this island only ever changes a
 * `max-height` and an opacity. Truncating the server output would pass every CI
 * check in this repo and still break the floor — `web/tests/skill-preview-ssr.test.ts`
 * asserts a string from the file's LAST section for exactly that reason.
 *
 * §8 also fixes the no-JS footer: with no JS the toggle island never renders, so
 * the footer reads `<n> lines · scroll to read …` and offers `Open the raw file`
 * as a plain anchor. `useIsHydrated()` (not `useState` + `useEffect`, which the
 * repo's `react-hooks/set-state-in-effect` lint rule rejects outright) is what
 * makes the server frame the no-JS frame.
 */

export interface SkillPreviewBodyProps {
  /** Server-rendered frontmatter band (§3.4's only structural distinction). */
  frontmatter: ReactNode;
  /** Server-rendered `<pre>` carrying the WHOLE body. Never a slice of it. */
  body: ReactNode;
  /** §3.4 footers, already substituted server-side (`{lines}`/`{collapsed}`). */
  footerCollapsed: string;
  footerExpanded: string;
  /** §8's no-JS footer — what the server HTML ships. */
  footerNoJs: string;
  expandLabel: string;
  collapseLabel: string;
  rawLabel: string;
  rawHref: string;
}

export function SkillPreviewBody({
  frontmatter,
  body,
  footerCollapsed,
  footerExpanded,
  footerNoJs,
  expandLabel,
  collapseLabel,
  rawLabel,
  rawHref,
}: SkillPreviewBodyProps) {
  // False in the server HTML and through hydration — so the server frame IS the
  // no-JS frame, and no toggle button exists for a no-JS visitor.
  const hydrated = useIsHydrated();
  const [expanded, setExpanded] = useState(false);
  const isExpanded = hydrated && expanded;

  return (
    <>
      {/* Everything inside this element is the served file, in file order —
          nothing else may go in here (see SKILL_FILE_DOM_ID). */}
      <div id={SKILL_FILE_DOM_ID}>
        {frontmatter}
        {/* The fade's containing block is this non-scrolling wrapper, NOT the
            scroller: an absolutely-positioned child of a scrolling box is
            anchored to the scrolled CONTENT, so §3.4's `inset:auto 0 0 0` would
            park the fade at the foot of the whole file, where it is never seen. Same
            result the design specifies, at the collapsed window's bottom edge. */}
        <div className="relative">
          <div
            // §9 / correction 9: focusable so it is keyboard-scrollable and can
            // take the global `:focus-visible` ring. No new CSS is needed.
            tabIndex={0}
            className={cn(
              "overflow-auto transition-[max-height] duration-150 ease-[ease]",
              isExpanded
                ? "max-h-[480px] app:max-h-[640px]"
                : "max-h-[300px] app:max-h-[380px]",
            )}
          >
            {body}
          </div>
          <div
            aria-hidden="true"
            className={cn(
              "pointer-events-none absolute inset-x-0 bottom-0 h-[110px] bg-[linear-gradient(to_bottom,rgba(255,255,255,0),var(--color-canvas)_78%)] transition-opacity duration-150 ease-[ease]",
              isExpanded && "opacity-0",
            )}
          />
        </div>
      </div>

      <div className="flex items-center justify-between gap-3 border-t border-hairline bg-surface px-3 py-[9px]">
        <p className="min-w-0 font-mono text-[11.5px] text-steel">
          {hydrated
            ? isExpanded
              ? footerExpanded
              : footerCollapsed
            : footerNoJs}
        </p>
        {hydrated ? (
          <button
            type="button"
            aria-expanded={isExpanded}
            onClick={() => setExpanded((value) => !value)}
            className={SKILL_CONTROL_CLASS}
          >
            {isExpanded ? collapseLabel : expandLabel}
          </button>
        ) : (
          <a href={rawHref} className={SKILL_CONTROL_CLASS}>
            {rawLabel}
          </a>
        )}
      </div>
    </>
  );
}
