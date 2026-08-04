import Link from "next/link";

import {
  Badge,
  buttonVariants,
  Card,
  Chip,
  EndpointCard,
  Section,
  Snippet,
} from "@/components/ui";
import { LANDING } from "@/content";
import { cn } from "@/lib/utils";

// Landing hero (P9.S6, build-prompt §7.3). Above the fold, so NO Reveal — it must
// paint immediately. Two columns on large screens: the value proposition (eyebrow
// + headline + sub + CTAs) beside the product proof — a real `POST /api/feedback`
// request panel (EndpointCard) layered over the "captured" record it produces
// (Korean message + disliked Badge + two Chip tags). Server component; the CTAs
// are anchor links styled with `buttonVariants`.
//
// The Korean message carries `break-keep` (word-break: keep-all) so an eojeol
// never splits across lines — the same locked floor globals.css applies to
// headings, made explicit here for the body-copy example.
//
// P11.S7 appends the install row (round 02 build-prompt §4) BELOW this grid.
// Nothing above this comment changed: the grid, the CTAs and the EndpointCard's
// P11.S1-corrected payload (nested `source.product`, no live-tier prefix) are
// untouched.

const { hero, heroInstall } = LANDING;

const requestText = `${hero.request.auth}
Content-Type: application/json

${hero.request.body}`;

export function Hero() {
  return (
    <Section tone="default" className="pt-12 md:pt-16">
      <div className="grid items-center gap-12 lg:grid-cols-2 lg:gap-16">
        {/* Left — the pitch. */}
        <div>
          <p className="inline-flex items-center gap-2 rounded-full bg-green-soft px-3 py-1 text-caption font-semibold text-green-dark">
            <span
              aria-hidden="true"
              className="size-1.5 rounded-full bg-green"
            />
            {hero.eyebrow}
          </p>

          <h1 className="mt-5 text-heading-1 text-ink sm:text-display-lg lg:text-hero-display">
            {hero.headline}
          </h1>

          <p className="mt-6 max-w-xl text-body-lg text-steel">{hero.sub}</p>

          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Link
              href={hero.ctaPrimary.href}
              className={buttonVariants({ variant: "primary", size: "lg" })}
            >
              {hero.ctaPrimary.label}
            </Link>
            <a
              href={hero.ctaSecondary.href}
              target="_blank"
              rel="noopener noreferrer"
              className={buttonVariants({ variant: "secondary", size: "lg" })}
            >
              {hero.ctaSecondary.label}
            </a>
          </div>
        </div>

        {/* Right — the proof: request panel layered over the captured record. */}
        <div className="relative">
          <EndpointCard label={`${hero.request.method} ${hero.request.path}`}>
            {requestText}
          </EndpointCard>

          <Card className="relative z-10 -mt-6 ml-auto w-[88%] shadow-[0_20px_48px_-24px_rgba(14,26,22,0.28)]">
            <div className="flex items-center justify-between gap-3">
              <span className="font-mono text-caption text-steel">
                {hero.captured.meta}
              </span>
              <Badge variant="disliked" dot>
                {hero.captured.rating}
              </Badge>
            </div>
            <p className="mt-3 text-body-md break-keep text-slate">
              {hero.captured.message}
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              {hero.captured.tags.map((tag) => (
                <Chip key={tag}>{tag}</Chip>
              ))}
            </div>
          </Card>
        </div>
      </div>

      {/* Install row (round 02 build-prompt §4) — never inside the grid above.
          `Start free` stays the primary CTA; this row is prominent by position,
          quiet by weight (a mono row + secondary copy button, never a filled
          button — result.md §6.1b). Narrow (<900px, `--breakpoint-app`): single
          column, label block above the snippet, caption drops its third clause
          via a CSS-only `app:` swap — never JS, to keep the no-JS floor and
          avoid a hydration mismatch. */}
      <div className="mt-11 grid grid-cols-1 items-center gap-[10px] border-t border-hairline pt-[26px] app:grid-cols-[auto_minmax(0,1fr)] app:gap-7">
        <div>
          <p className="font-mono text-micro text-green-dark uppercase">
            {heroInstall.label}
          </p>
          <p className="mt-1 max-w-[22ch] text-body-sm text-steel">
            {heroInstall.sub}
          </p>
        </div>

        <div className="min-w-0">
          <Snippet
            variant="row"
            command={heroInstall.command}
            copy={{
              ...LANDING.snippet,
              announcement: heroInstall.copyAnnouncement,
            }}
          />
          <p className="mt-2 font-mono text-[11.5px] text-steel">
            <span className="app:hidden">{heroInstall.captionNarrow}</span>
            <span className="hidden app:block">{heroInstall.caption}</span>
          </p>
        </div>
      </div>
    </Section>
  );
}
