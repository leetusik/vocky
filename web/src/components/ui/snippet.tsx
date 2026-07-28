"use client";

import { cva, type VariantProps } from "class-variance-authority";
import {
  Fragment,
  type HTMLAttributes,
  type ReactNode,
  type Ref,
  useEffect,
  useRef,
  useState,
} from "react";

import { attemptCopy, type CopyState } from "@/lib/clipboard";
import { useIsHydrated } from "@/lib/use-is-hydrated";
import { cn } from "@/lib/utils";

/**
 * Snippet — a copyable command (round 02, build-prompt §3.1 / §7 / §8).
 *
 * One primitive, two variants: `row` (one line, light, 48px, inline button) and
 * `block` (multi-line, dark, label + button in a bar). The block deliberately
 * inherits the shipped `EndpointCard` palette so a terminal on the landing looks
 * like a request panel elsewhere on it.
 *
 * THREE LOCKED FLOORS, none of which had precedent in this repo before P11.S6 —
 * they are the contract, not styling details:
 *
 * 1. NO WRAP, EVER. The command element carries `whitespace-pre overflow-x-auto`
 *    (and, in the row, `flex-1 min-w-0` so the flex parent will actually let it
 *    shrink). A `curl … | bash` line must paste back as ONE unbroken line from any
 *    viewport width — horizontal scroll is correct, reflow is a bug (§11.1).
 *
 * 2. THE CLIPBOARD GETS THE DOM NODE'S `textContent`, never a separately-typed
 *    string. That is why `command` is rendered into a ref'd `<code>` / `<pre>` and
 *    read back at click time, and why the block's comment lines — recoloured with
 *    a `<span>`, which does not change `textContent` — are still copied verbatim
 *    (they are valid shell).
 *
 * 3. THE BUTTON IS ABSENT WITHOUT JS, NOT INERT. §8 is explicit: a no-JS visitor
 *    sees NO button at all. So the button renders only once `useIsHydrated()` has
 *    flipped, exactly the way `ui/reveal.tsx` treats the static page as the
 *    guaranteed baseline: the server HTML is the bordered, padded, SELECTABLE
 *    snippet, and JS only ever ADDS the button. Never render it disabled instead —
 *    a present-but-dead control is the failure mode this gate exists to prevent.
 *
 * States (§7) are deliberately ASYMMETRIC: success reverts to idle after exactly
 * 2000ms, failure PERSISTS until the next attempt. A state that fixed nothing must
 * not disappear on its own — on failure the command text is instead selected
 * programmatically (`Range` + `Selection`) and a hint names the manual shortcut.
 * The revert timer is cleared on unmount so it can never fire into a dead tree.
 *
 * A11y: one POLITE live region per snippet, which receives the snippet's own
 * announcement on success only. Nothing is announced on failure — the selection
 * plus the visible hint is the affordance. No `role="alert"` anywhere in round 02.
 *
 * Copy-as-data: every string arrives through `copy` (the `ShowOnceKeyCopy`
 * precedent). The only literals here are token class names and one internal
 * invariant error — no user-facing copy lives in this file.
 */

/** §7: the copied state reverts to idle after exactly this long. */
const COPIED_REVERT_MS = 2000;

export const snippetVariants = cva("", {
  variants: {
    variant: {
      // §3.1 row: 48px, 5px 6px 5px 14px, hairline-strong on canvas, radius 10.
      row: "flex min-h-12 items-center gap-2.5 rounded-lg border border-hairline-strong bg-canvas py-[5px] pr-1.5 pl-3.5",
      // §3.1 block: forest-soft on forest-mid, radius 12 (no token lands on 12),
      // `overflow-hidden` so the bar's corners clip with the panel's.
      block:
        "overflow-hidden rounded-[12px] border border-forest-soft bg-forest-mid",
    },
  },
  defaultVariants: {
    variant: "row",
  },
});

/**
 * The `cbtn` of §3.1, plus its §7 states. Not exported: the state is owned by
 * `Snippet`, never set from outside. `failed` is intentionally identical on light
 * and dark — §7 gives a dark override for `copied` only, and the caution chip
 * reads on both surfaces.
 */
const copyButtonVariants = cva(
  "inline-flex min-h-9 shrink-0 items-center justify-center rounded-md border px-3 font-mono text-caption tracking-[.3px] transition-colors duration-150 ease-[ease] focus-visible:outline-none",
  {
    variants: {
      tone: { light: "", dark: "" },
      state: { idle: "", copied: "", failed: "" },
    },
    compoundVariants: [
      {
        tone: "light",
        state: "idle",
        class:
          "border-hairline-strong bg-canvas text-slate hover:bg-surface hover:text-charcoal",
      },
      {
        tone: "dark",
        state: "idle",
        class:
          "border-hairline-dark bg-transparent text-on-dark-muted hover:bg-white/10 hover:text-on-dark",
      },
      {
        tone: "light",
        state: "copied",
        class: "border-security-mint bg-green-soft text-green-dark",
      },
      {
        tone: "dark",
        state: "copied",
        class:
          "border-security-teal bg-[rgba(190,233,213,0.16)] text-victory-lime",
      },
      {
        state: "failed",
        class: "border-hairline-caution bg-surface-caution text-caution-deep",
      },
    ],
    defaultVariants: {
      tone: "light",
      state: "idle",
    },
  },
);

/**
 * Copy strings for one snippet. The first four are universal (they live once in
 * `LANDING.snippet`); `announcement` is per-snippet, since a polite live region
 * that says "Copied." four times on one page tells a screen-reader user nothing.
 */
export interface SnippetCopy {
  /** Idle button label. */
  copyLabel: string;
  /** Button label during the 2s copied state — carries its own ✓ glyph. */
  copiedLabel: string;
  /** Button label after a failed attempt; persists until the next attempt. */
  copyFailedLabel: string;
  /** Hint under the snippet naming the manual shortcut. Failure only. */
  selectionHint: string;
  /** Polite live-region sentence, announced on success only. */
  announcement: string;
}

export interface SnippetProps
  extends
    Omit<HTMLAttributes<HTMLDivElement>, "children">,
    VariantProps<typeof snippetVariants> {
  /**
   * `block`: the bar's label (always pass one — the bar renders regardless, since
   * §8 keeps it in the no-JS HTML). `row`: an optional leading tag.
   */
  label?: ReactNode;
  /** The exact bytes shown AND copied. Never reflowed, never re-quoted. */
  command: string;
  copy: SnippetCopy;
}

/**
 * §3.1: comment lines inside a block render `trust-sage` and ARE included in the
 * copy (they are valid shell). The recolouring `<span>` does not affect
 * `textContent`, so the clipboard still gets the command byte for byte.
 */
function renderBlockLines(command: string) {
  const lines = command.split("\n");
  return lines.map((line, index) => (
    <Fragment key={index}>
      {line.trimStart().startsWith("#") ? (
        <span className="text-trust-sage">{line}</span>
      ) : (
        line
      )}
      {index < lines.length - 1 ? "\n" : null}
    </Fragment>
  ));
}

export function Snippet({
  className,
  variant = "row",
  label,
  command,
  copy,
  ...props
}: SnippetProps) {
  const commandRef = useRef<HTMLElement>(null);
  const revertRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [state, setState] = useState<CopyState>("idle");
  // Floor 3: false in the server HTML and through hydration, so the button
  // simply does not exist for a no-JS visitor.
  const mounted = useIsHydrated();

  // The 2s revert must never fire into an unmounted tree.
  useEffect(
    () => () => {
      if (revertRef.current !== null) clearTimeout(revertRef.current);
    },
    [],
  );

  function clearRevert() {
    if (revertRef.current !== null) {
      clearTimeout(revertRef.current);
      revertRef.current = null;
    }
  }

  /** Floor 2: the clipboard reads the rendered node, not the `command` prop. */
  function readCommandText() {
    const node = commandRef.current;
    if (node === null) throw new Error("Snippet: command node is not mounted");
    return node.textContent ?? "";
  }

  /**
   * §7 failure affordance: select the command so ⌘C/Ctrl+C works. Deliberately
   * NOT extracted into `lib/clipboard.ts` — it is pure DOM and would be untestable
   * there anyway; the helper stays DOM-free so it can be tested in Node.
   */
  function selectCommandText() {
    const node = commandRef.current;
    if (node === null || typeof window === "undefined") return;
    const selection = window.getSelection();
    if (selection === null) return;
    const range = document.createRange();
    range.selectNodeContents(node);
    selection.removeAllRanges();
    selection.addRange(range);
  }

  async function handleCopy() {
    clearRevert();
    const next = await attemptCopy(readCommandText, (text) =>
      navigator.clipboard.writeText(text),
    );
    setState(next);
    if (next === "copied") {
      revertRef.current = setTimeout(() => {
        revertRef.current = null;
        setState("idle");
      }, COPIED_REVERT_MS);
    } else {
      selectCommandText();
    }
  }

  const isBlock = variant === "block";
  const buttonLabel =
    state === "copied"
      ? copy.copiedLabel
      : state === "failed"
        ? copy.copyFailedLabel
        : copy.copyLabel;

  const button = mounted ? (
    <button
      type="button"
      onClick={handleCopy}
      className={copyButtonVariants({
        tone: isBlock ? "dark" : "light",
        state,
      })}
    >
      {buttonLabel}
    </button>
  ) : null;

  return (
    <div className={cn(className)} {...props}>
      <div
        className={cn(
          snippetVariants({ variant }),
          // §7: on failure the snippet's own border goes caution too.
          state === "failed" && "border-hairline-caution",
        )}
      >
        {isBlock ? (
          <>
            <div className="flex items-center justify-between gap-2.5 border-b border-hairline-dark bg-ink py-[7px] pr-2 pl-3.5">
              <span className="font-mono text-micro tracking-[.7px] text-trust-sage uppercase">
                {label}
              </span>
              {button}
            </div>
            <pre
              ref={commandRef as Ref<HTMLPreElement>}
              className="overflow-x-auto p-3.5 font-mono text-code-md leading-[1.65] whitespace-pre text-[#DCEBE3]"
            >
              {renderBlockLines(command)}
            </pre>
          </>
        ) : (
          <>
            {label != null && (
              <span className="shrink-0 font-mono text-micro tracking-[.7px] text-green-dark uppercase">
                {label}
              </span>
            )}
            <code
              ref={commandRef as Ref<HTMLElement>}
              className="min-w-0 flex-1 overflow-x-auto font-mono text-[13.5px] leading-[1.5] whitespace-pre text-ink"
            >
              {command}
            </code>
            {button}
          </>
        )}
      </div>

      {state === "failed" && (
        <p className="mt-2 font-mono text-[11.5px] text-caution-deep">
          {copy.selectionHint}
        </p>
      )}

      {/* Polite, per-snippet, success only. Never `role="alert"` (§7, §9). */}
      <span aria-live="polite" className="sr-only">
        {state === "copied" ? copy.announcement : ""}
      </span>
    </div>
  );
}
