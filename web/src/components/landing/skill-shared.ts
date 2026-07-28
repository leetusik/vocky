/**
 * The two constants round 02's skill surface shares across its server component
 * and its two client islands (P11.S9).
 *
 * They live in a PLAIN module on purpose: every export of a `"use client"` file
 * becomes a client reference in the RSC graph, so a server component cannot
 * import a bare string from one. Keeping them here also stops the control class
 * from drifting between the pane's header (server) and its footer (client) —
 * they are one treatment, painted twice.
 *
 * Neither string is copy: an element id and a class list, nothing a reader sees.
 */

/**
 * The pane element whose `textContent` IS the served file, byte for byte
 * (frontmatter band + body, in file order — the split in `skill-preview.tsx` is
 * lossless). Round 02's locked clipboard rule (build-prompt §3.1) is "copy the
 * DOM node's textContent, never a separately-typed string", and `SkillCopyButton`
 * — which renders outside this subtree, in the section's left column — finds it
 * by this id. Nothing else may be rendered inside that element.
 */
export const SKILL_FILE_DOM_ID = "skill-file-content";

/**
 * §3.1's `cbtn`, light tone: the round's only small-control shape. Worn by the
 * pane header's `Download` anchor and by the footer's toggle / `Open the raw
 * file` anchor, so the footer does not reflow when JS arrives and swaps one for
 * the other. `SkillCopyButton` re-states the same treatment through a CVA
 * because it also carries §7's `copied` / `failed` states.
 */
export const SKILL_CONTROL_CLASS =
  "inline-flex min-h-9 shrink-0 items-center justify-center rounded-md border border-hairline-strong bg-canvas px-3 font-mono text-caption tracking-[.3px] text-slate transition-colors duration-150 ease-[ease] hover:bg-surface hover:text-charcoal focus-visible:outline-none";
