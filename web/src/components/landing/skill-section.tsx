import { buttonVariants, Section } from "@/components/ui";
import { LANDING } from "@/content";
import { cn } from "@/lib/utils";

import { INLINE_CODE_CLASS, withInlineCode } from "./inline-code";
import { SkillCopyButton } from "./skill-copy-button";
import { SkillPreview } from "./skill-preview";

/**
 * SkillSection (round 02, build-prompt §6) — page position 5, id `skill`.
 *
 * The round's third surface and the target of `AgentQuickstart`'s peer link,
 * which has pointed at `#skill` since P11.S8 and resolves as of this slice. A
 * sticky pitch on the left, the served file itself on the right — the section's
 * whole argument is that the skill is a real published artifact, so the pane
 * shows the actual bytes `/SKILL.md` serves rather than a description of them
 * (see `skill-preview.tsx`).
 *
 * Server component; the only client islands are `SkillCopyButton` (mount-gated,
 * absent entirely without JS) and the pane's expand toggle. **`Download
 * SKILL.md` is a plain `<a download>`** — §8's locked no-JS survivor, and the
 * reason a client-only Copy is acceptable beside it.
 *
 * Two corrections from `P11.DECOMP2` (`phase.md`) apply:
 *
 * 4. The eyebrow is the hero's dotted-pill treatment, not `how-it-works.tsx`'s
 *    plain uppercase one — §5 names the dot explicitly for the sibling section
 *    and §6's eyebrow is unqualified, so it takes the same treatment (never the
 *    plainer fallback).
 * 7. "Collapsed" is a visual window, not a truncation — the whole file is in the
 *    server HTML. Enforced in `skill-preview-body.tsx` and asserted in
 *    `web/tests/skill-preview-ssr.test.ts`.
 *
 * `LANDING.skill` is ALL of this section's copy, already final — this file
 * writes none (§11.4).
 */

const { skill } = LANDING;

export function SkillSection() {
  return (
    <Section tone="surfaceSoft" id="skill" reveal>
      <div className="grid grid-cols-1 items-start gap-14 app:grid-cols-[minmax(0,0.82fr)_minmax(0,1.18fr)]">
        {/* Left — sticky at >=900px only; narrow drops it and the pane simply
            falls below in DOM order (§6). */}
        <div className="app:sticky app:top-6">
          {/* Correction 4: the hero's dotted-pill eyebrow. */}
          <p className="inline-flex items-center gap-2 rounded-full bg-green-soft px-3 py-1 text-caption font-semibold text-green-dark">
            <span
              aria-hidden="true"
              className="size-1.5 rounded-full bg-green"
            />
            {skill.eyebrow}
          </p>
          <h2 className="mt-3 text-heading-2 text-ink">{skill.heading}</h2>
          <p
            className={cn(
              "mt-4 max-w-[46ch] text-[15px] leading-[1.6] text-steel",
              INLINE_CODE_CLASS,
            )}
          >
            {withInlineCode(skill.lede.text, skill.lede.code)}
          </p>

          {/* Actions — full-width stacked below 900px, side by side above. */}
          <div className="mt-[22px] flex flex-col items-start gap-3 app:flex-row app:items-center">
            <SkillCopyButton
              variant="primary"
              className="w-full app:w-auto"
              label={skill.copyAction}
              copiedLabel={LANDING.snippet.copiedLabel}
              failedLabel={LANDING.snippet.copyFailedLabel}
              selectionHint={LANDING.snippet.selectionHint}
              announcement={skill.copyAnnouncement}
            />
            {/* §8: a plain anchor, always present, JS or no JS. */}
            <a
              href={skill.downloadHref}
              download
              className={cn(
                buttonVariants({ variant: "secondary" }),
                "w-full app:w-auto",
              )}
            >
              {skill.downloadAction}
            </a>
          </div>

          <p className="mt-3 font-mono text-[11.5px] text-steel">
            {skill.served}
          </p>

          <div className="mt-7 border-t border-hairline-soft pt-6">
            <p className="font-mono text-micro text-green-dark uppercase">
              {skill.insideLabel}
            </p>
            <ol className="mt-3 space-y-2">
              {skill.inside.map((item, index) => (
                <li
                  key={item}
                  className="flex items-baseline gap-3 text-body-sm text-slate"
                >
                  <span className="font-mono text-[11.5px] text-steel tabular-nums">
                    {index + 1}
                  </span>
                  <span>{item}</span>
                </li>
              ))}
            </ol>
          </div>
        </div>

        {/* Right — the served file, collapsed by default. */}
        <SkillPreview />
      </div>
    </Section>
  );
}
