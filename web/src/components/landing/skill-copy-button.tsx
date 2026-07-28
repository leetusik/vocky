"use client";

import { cva } from "class-variance-authority";
import { useEffect, useRef, useState } from "react";

import { attemptCopy, type CopyState } from "@/lib/clipboard";
import { useIsHydrated } from "@/lib/use-is-hydrated";
import { cn } from "@/lib/utils";

import { SKILL_FILE_DOM_ID } from "./skill-shared";

/**
 * SkillCopyButton — "copy the whole served file", used twice (round 02,
 * build-prompt §3.4 header + §6 primary action).
 *
 * It is the `Snippet` copy island's shape, with one difference that matters:
 * the two buttons sit in DIFFERENT subtrees (the pane header, and the section's
 * left column) while copying the SAME node, so the source is found by
 * `SKILL_FILE_DOM_ID` instead of a local ref. The locked clipboard rule (§3.1)
 * is unchanged and is the whole point: the clipboard gets the pane's rendered
 * `textContent`, never a separately-typed string and never a pasted excerpt —
 * so what the visitor copies is byte-for-byte what `scripts/skill_parity.py`
 * gates and what `/SKILL.md` serves.
 *
 * §8: the button renders ONLY after hydration. A no-JS visitor sees no button at
 * all — never a present-but-inert one — which is exactly why the section's
 * `Download SKILL.md` is a plain anchor and the pane's footer offers the raw
 * file. §7's states are asymmetric, same as `Snippet`: `copied` reverts after
 * 2000ms, `failed` persists until the next attempt and instead selects the pane
 * text so ⌘C/Ctrl+C works.
 *
 * No copy lives here — every string arrives through props from `LANDING.skill`
 * / `LANDING.snippet` (§11.4).
 */

/** §7: the copied state reverts to idle after exactly this long. */
const COPIED_REVERT_MS = 2000;

/**
 * Deliberately a local CVA rather than an export of `ui/snippet.tsx`'s private
 * `copyButtonVariants`: that one is documented there as owned by `Snippet` and
 * covers the compact `cbtn` only, while this needs the same three §7 states on
 * the section's PRIMARY filled button too. Colour lives entirely in the
 * compound variants (never stacked over a base `bg-*`), because two competing
 * background utilities have no guaranteed source-order tiebreak in the compiled
 * cascade — the trap `P11.S8` recorded for `text-caption font-bold`.
 */
const skillCopyVariants = cva(
  "inline-flex w-full items-center justify-center rounded-md transition-colors duration-150 ease-[ease] focus-visible:outline-none",
  {
    variants: {
      variant: {
        // §3.1's `cbtn`, light tone — the pane header's Copy.
        compact: "min-h-9 border px-3 font-mono text-caption tracking-[.3px]",
        // §6's primary filled action. `border-transparent` keeps the box the
        // same height in all three states (copied/failed add a visible border).
        primary:
          "min-h-10 border border-transparent px-[18px] py-2 font-en text-button-md font-semibold",
      },
      state: { idle: "", copied: "", failed: "" },
    },
    compoundVariants: [
      {
        variant: "compact",
        state: "idle",
        class:
          "border-hairline-strong bg-canvas text-slate hover:bg-surface hover:text-charcoal",
      },
      {
        variant: "primary",
        state: "idle",
        class:
          "bg-green text-on-primary shadow-[0_10px_24px_-12px_rgba(12,122,82,0.5)] hover:-translate-y-0.5 hover:bg-green-deep hover:shadow-[0_14px_30px_-12px_rgba(12,122,82,0.62)]",
      },
      {
        state: "copied",
        class: "border-security-mint bg-green-soft text-green-dark",
      },
      {
        state: "failed",
        class: "border-hairline-caution bg-surface-caution text-caution-deep",
      },
    ],
    defaultVariants: { variant: "compact", state: "idle" },
  },
);

export interface SkillCopyButtonProps {
  variant: "compact" | "primary";
  /** Idle label. */
  label: string;
  /** §7's 2s success label (carries its own ✓ glyph). */
  copiedLabel: string;
  /** §7's persisting failure label. */
  failedLabel: string;
  /** Polite live-region sentence, announced on success only. */
  announcement: string;
  /**
   * §7's failure hint. Omitted for the pane header, where there is no room in a
   * 9px-padded bar and the programmatic selection is directly visible in the
   * pane one line below the button.
   */
  selectionHint?: string;
  /** Layout only (width/margin) — never a restyle of the button itself. */
  className?: string;
}

/** The pane node whose `textContent` is the file. */
function skillFileNode() {
  return typeof document === "undefined"
    ? null
    : document.getElementById(SKILL_FILE_DOM_ID);
}

export function SkillCopyButton({
  variant,
  label,
  copiedLabel,
  failedLabel,
  announcement,
  selectionHint,
  className,
}: SkillCopyButtonProps) {
  const revertRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [state, setState] = useState<CopyState>("idle");
  const hydrated = useIsHydrated();

  // The 2s revert must never fire into an unmounted tree.
  useEffect(
    () => () => {
      if (revertRef.current !== null) clearTimeout(revertRef.current);
    },
    [],
  );

  /** Locked rule: read the rendered pane, not a string typed in this file. */
  function readSkillText() {
    const node = skillFileNode();
    if (node === null)
      throw new Error("SkillCopyButton: skill pane is not mounted");
    return node.textContent ?? "";
  }

  /** §7's failure affordance: select the file so ⌘C/Ctrl+C works. */
  function selectSkillText() {
    const node = skillFileNode();
    if (node === null || typeof window === "undefined") return;
    const selection = window.getSelection();
    if (selection === null) return;
    const range = document.createRange();
    range.selectNodeContents(node);
    selection.removeAllRanges();
    selection.addRange(range);
  }

  async function handleCopy() {
    if (revertRef.current !== null) {
      clearTimeout(revertRef.current);
      revertRef.current = null;
    }
    const next = await attemptCopy(readSkillText, (text) =>
      navigator.clipboard.writeText(text),
    );
    setState(next);
    if (next === "copied") {
      revertRef.current = setTimeout(() => {
        revertRef.current = null;
        setState("idle");
      }, COPIED_REVERT_MS);
    } else {
      selectSkillText();
    }
  }

  // §8: absent without JS, never inert.
  if (!hydrated) return null;

  const buttonLabel =
    state === "copied" ? copiedLabel : state === "failed" ? failedLabel : label;

  return (
    <span className={cn("inline-flex flex-col items-stretch gap-2", className)}>
      <button
        type="button"
        onClick={handleCopy}
        className={skillCopyVariants({ variant, state })}
      >
        {buttonLabel}
      </button>
      {state === "failed" && selectionHint !== undefined && (
        <span className="font-mono text-[11.5px] text-caution-deep">
          {selectionHint}
        </span>
      )}
      {/* Polite, per-button, success only — never an assertive alert role, which
          round 02 forbids outright (§7, §9). The wording here deliberately avoids
          spelling that attribute so S10's grep for it stays mechanical. */}
      <span aria-live="polite" className="sr-only">
        {state === "copied" ? announcement : ""}
      </span>
    </span>
  );
}
