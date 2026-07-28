import type { ReactNode } from "react";

/**
 * The landing's shared inline-`<code>` treatment for round 02's "rich strings"
 * (build-prompt §5.1 / §6): one verbatim sentence plus the list of substrings
 * that must render as inline code.
 *
 * Lifted verbatim from `agent-quickstart.tsx` at P11.S9, which is the point the
 * helper got its second consumer (`LANDING.skill.lede` is the same
 * `{ text, code[] }` shape as `quickstart.steps.env.note`). S8 deliberately left
 * it file-private under this phase's "one consumer, build inline" pattern and
 * flagged the promotion decision to this slice; two consumers is where a
 * duplicated ~12-line splitter starts being able to drift, and the design wants
 * both sentences to read as ONE treatment, so it is promoted rather than copied.
 * Behaviour is unchanged — `agent-quickstart.tsx` now imports what it defined.
 */

/**
 * §3.2's inline-code recipe (mono 12.5px on a faint ink wash). Applied to the
 * PARENT as a descendant variant so callers can write plain `<code>` — the same
 * mechanism `ui/trap.tsx` uses for the trap body.
 */
export const INLINE_CODE_CLASS =
  "[&_code]:rounded-xs [&_code]:bg-[rgba(14,26,22,0.055)] [&_code]:px-[5px] [&_code]:py-px [&_code]:font-mono [&_code]:text-[12.5px]";

/**
 * Split `text` on every occurrence of every token in `code` and wrap the matches
 * in `<code>`. Keyed off the same `code[]` array the copy already carries —
 * rather than hand-splitting the sentence at authoring time, which would hide a
 * transcription slip at a segment boundary. Longest token first so a token that
 * happens to prefix another can never win the wrong match (not the case in this
 * round's copy, but cheap insurance).
 */
export function withInlineCode(
  text: string,
  code: readonly string[],
): ReactNode {
  if (code.length === 0) return text;
  const tokens = [...code].sort((a, b) => b.length - a.length);
  const pattern = new RegExp(
    `(${tokens.map((token) => token.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})`,
    "g",
  );
  return text
    .split(pattern)
    .filter((part) => part.length > 0)
    .map((part, index) =>
      code.includes(part) ? <code key={index}>{part}</code> : part,
    );
}
