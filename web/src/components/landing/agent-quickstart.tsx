import Link from "next/link";
import type { ReactNode } from "react";

import { Card, Chip, Section, Snippet, Trap } from "@/components/ui";
import { LANDING } from "@/content";
import { cn } from "@/lib/utils";

import { INLINE_CODE_CLASS, withInlineCode } from "./inline-code";

/**
 * AgentQuickstart (round 02, build-prompt §5) — page position 4, id `quickstart`.
 * The biggest of round 02's three surfaces: a header, four numbered steps (each a
 * different shape), a fifth "peer" row linking to `#skill` (S9), and a sticky
 * contract aside. Server component throughout; the only client islands are the
 * `Snippet` copy buttons it composes (mount-gated, so a no-JS visitor sees the
 * selectable command and no button at all — see `ui/snippet.tsx`).
 *
 * `LANDING.quickstart` is ALL of this section's copy, already final — this file
 * writes none. `steps` is an object keyed `install`/`env`/`verify`/`capture`
 * (four different shapes), not an array, so each step is rendered explicitly.
 *
 * Three corrections from `P11.DECOMP2` apply here (`phase.md`):
 *
 * 3. The `.note` treatment (13px `text-steel`, `border-left:2px solid green`,
 *    `padding-left:12px`) does not exist anywhere in the repo — it is built
 *    INLINE below, once. It is not promoted to a `ui/` primitive: it has exactly
 *    one consumer (step 2).
 * 4. The eyebrow reuses `hero.tsx`'s dotted-pill treatment, not `how-it-works.tsx`'s
 *    plain uppercase one — §5 names the dot explicitly.
 * 5. The step marker is the EXPLICIT values §5.1 gives (34px circle, ink bg,
 *    white mono 700 15px) — not the actually-shipped `HowItWorks` numeral
 *    (36px, green-soft/green-dark) that the spec's prose mislabels. Do not
 *    "fix" this file to match `how-it-works.tsx`, and do not restyle
 *    `how-it-works.tsx` to match this file.
 *
 * Two content floors that must never be softened (they are product truth, not
 * styling): `400` is the SUCCESS reading on the verify step (the token
 * authenticated; a bare GET was rejected only for a missing filter) — never
 * relabelled or reordered below `401`. And `401` says stop, with no retry
 * advice ever, because the published `skills/vocky-feedback/SKILL.md` tells
 * agents to stop on 401 and this page must not contradict it.
 */

const { quickstart } = LANDING;
const { steps, peer, aside } = quickstart;

/**
 * §5.1 / §6's "rich strings" (one verbatim sentence + the substrings that render
 * as inline `<code>`) moved to `./inline-code` at P11.S9, unchanged: `§6`'s
 * `skill.lede` is the same `{ text, code[] }` shape, and one splitter shared by
 * both sections cannot drift the way two copies can.
 */

/** §3.3 — colour by code; the chip always repeats the literal code too, so
 * colour is never the sole signal. Anything other than 400/401 (here, "else")
 * falls through to the caution tone. */
const READING_CHIP_TONE: Record<string, string> = {
  "400": "bg-green-soft text-green-dark",
  "401": "bg-surface-danger text-danger-deep",
};

function ReadingList({ readings }: { readings: typeof steps.verify.readings }) {
  return (
    <ul className="divide-y divide-hairline-soft">
      {readings.map((reading) => (
        <li
          key={reading.code}
          className="flex items-start gap-3 py-[11px] text-[13.5px] leading-[1.55] text-slate"
        >
          <span
            className={cn(
              "flex min-w-[52px] shrink-0 items-center justify-center rounded-sm px-2 py-[3px] font-mono text-[12px] font-bold",
              READING_CHIP_TONE[reading.code] ?? "bg-surface-caution text-caution-deep",
            )}
          >
            {reading.code}
          </span>
          <span>
            {reading.verdict && (
              <span className="font-semibold text-charcoal">{reading.verdict} </span>
            )}
            {reading.body}
          </span>
        </li>
      ))}
    </ul>
  );
}

/** §5.1's step marker (correction 5): 34px circle, ink bg, white mono 700 15px.
 * The peer row's `·` marker reuses the same shape, `bg-surface-soft`/`text-steel`
 * instead, per §5.1's own fifth-step-row framing. */
function StepMarker({ tone, children }: { tone: "step" | "peer"; children: ReactNode }) {
  return (
    <span
      className={cn(
        "flex size-[34px] shrink-0 items-center justify-center rounded-full font-mono text-[15px] font-bold",
        tone === "step" ? "bg-ink text-on-dark" : "bg-surface-soft text-steel",
      )}
    >
      {children}
    </span>
  );
}

export function AgentQuickstart() {
  return (
    <Section tone="default" id="quickstart" reveal>
      <div className="max-w-[70ch]">
        {/* Correction 4: the hero's dotted-pill eyebrow, not how-it-works.tsx's
            plain uppercase one — §5 names the dot explicitly. */}
        <p className="inline-flex items-center gap-2 rounded-full bg-green-soft px-3 py-1 text-caption font-semibold text-green-dark">
          <span aria-hidden="true" className="size-1.5 rounded-full bg-green" />
          {quickstart.eyebrow}
        </p>
        <h2 className="mt-3 text-heading-1 text-ink">{quickstart.heading}</h2>
        <p className="mt-4 text-body-lg text-steel">{quickstart.lede}</p>
      </div>

      <div className="mt-11 grid grid-cols-1 items-start gap-14 app:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)]">
        {/* Left — four numbered steps (each a different shape) + the peer row. */}
        <ol className="flex flex-col gap-4">
          <li className="flex items-start gap-4">
            <StepMarker tone="step">{steps.install.n}</StepMarker>
            <div className="min-w-0 flex-1 pb-[34px]">
              <h3 className="text-heading-4 text-charcoal">{steps.install.title}</h3>
              <p className="mt-2 max-w-[62ch] text-body-md text-steel">{steps.install.sub}</p>
              <div className="mt-3.5">
                <Snippet
                  variant="row"
                  command={steps.install.command}
                  copy={{ ...LANDING.snippet, announcement: steps.install.copyAnnouncement }}
                />
              </div>
            </div>
          </li>

          <li className="flex items-start gap-4">
            <StepMarker tone="step">{steps.env.n}</StepMarker>
            <div className="min-w-0 flex-1 pb-[34px]">
              <h3 className="text-heading-4 text-charcoal">{steps.env.title}</h3>
              <div className="mt-3.5 space-y-3">
                <Snippet
                  variant="block"
                  label={steps.env.snippetLabel}
                  command={steps.env.command}
                  copy={{ ...LANDING.snippet, announcement: steps.env.copyAnnouncement }}
                />
                {/* Correction 3: the ".note" treatment does not exist in this
                    repo — built inline, one consumer. Order matters: note
                    before trap. */}
                <div
                  className={cn(
                    "border-l-2 border-green pl-3 text-body-sm text-steel",
                    INLINE_CODE_CLASS,
                  )}
                >
                  {withInlineCode(steps.env.note.text, steps.env.note.code)}
                </div>
                <Trap label={steps.env.trap.label}>
                  {withInlineCode(steps.env.trap.body.text, steps.env.trap.body.code)}
                </Trap>
              </div>
            </div>
          </li>

          <li className="flex items-start gap-4">
            <StepMarker tone="step">{steps.verify.n}</StepMarker>
            <div className="min-w-0 flex-1 pb-[34px]">
              <h3 className="text-heading-4 text-charcoal">{steps.verify.title}</h3>
              <p className="mt-2 max-w-[62ch] text-body-md text-steel">{steps.verify.sub}</p>
              <div className="mt-3.5 space-y-3">
                <Snippet
                  variant="block"
                  label={steps.verify.snippetLabel}
                  command={steps.verify.command}
                  copy={{ ...LANDING.snippet, announcement: steps.verify.copyAnnouncement }}
                />
                {/* 400 is the SUCCESS reading; 401 says stop, never retry — see
                    the file header. Do not relabel or reorder either. */}
                <ReadingList readings={steps.verify.readings} />
              </div>
            </div>
          </li>

          <li className="flex items-start gap-4">
            <StepMarker tone="step">{steps.capture.n}</StepMarker>
            <div className="min-w-0 flex-1 pb-[34px]">
              <h3 className="text-heading-4 text-charcoal">{steps.capture.title}</h3>
              <div className="mt-3.5">
                <Snippet
                  variant="row"
                  command={steps.capture.command}
                  copy={{ ...LANDING.snippet, announcement: steps.capture.copyAnnouncement }}
                />
                <div className="mt-2.5 flex items-center gap-2">
                  <span className="inline-flex items-center rounded-full bg-green-soft px-2.5 py-1 font-mono text-[11px] text-green-dark">
                    {steps.capture.resultBadge}
                  </span>
                  <span className="font-mono text-[11.5px] text-steel">
                    {steps.capture.resultText}
                  </span>
                </div>
              </div>
            </div>
          </li>

          {/* Peer row — a fifth row with a "·" marker instead of a numeral. The
              `#skill` anchor exists from P11.S6 so this compiles now; it
              resolves once P11.S9 lands the section — by design, not a stub. */}
          <li className="flex items-center gap-4">
            <StepMarker tone="peer">·</StepMarker>
            <p className="text-body-md text-steel">
              {peer.before}
              <Link
                href={peer.href}
                className="font-semibold text-green-dark underline underline-offset-2 hover:text-green-deep"
              >
                {peer.linkLabel}
              </Link>
              {peer.after}
            </p>
          </li>
        </ol>

        {/* Right — the contract aside. Sticky only at >=900px (app:); narrow
            drops sticky and the aside simply falls below the steps in DOM
            order (nothing reorders). */}
        <div className="app:sticky app:top-6 flex flex-col gap-4">
          <Card variant="featureMuted">
            <p className="font-mono text-micro text-green-dark uppercase">
              {aside.contractLabel}
            </p>
            <div className="mt-3 space-y-2">
              {aside.contractRows.map((row) => (
                <Chip key={row.name} className="flex w-full items-center justify-between bg-canvas">
                  <span>{row.name}</span>
                  <span>{row.value}</span>
                </Chip>
              ))}
            </div>
            <div className="mt-4 border-t border-hairline-soft pt-4">
              <p className="text-body-sm text-steel">{aside.contractBody}</p>
            </div>
          </Card>

          <Card>
            <p className="font-mono text-micro text-green-dark uppercase">
              {aside.worksWithLabel}
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              {aside.worksWith.map((item) => (
                <Chip key={item}>{item}</Chip>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </Section>
  );
}
