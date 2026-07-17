import { Card, Grid, Section } from "@/components/ui";
import { LANDING } from "@/content";

// "How it works" (P9.S6, build-prompt §7.3). Three grounded steps from minting a
// key to searching the captured signal, in a `Grid cols={3}` of cards. Anchored
// `#how` for the nav. `<Section reveal>` gives it a one-shot scroll reveal
// (reduced-motion-safe via the Reveal island).

const { how } = LANDING;

export function HowItWorks() {
  return (
    <Section id="how" tone="surface" reveal>
      <div className="max-w-2xl">
        <p className="text-caption font-semibold tracking-[0.12em] text-green-dark uppercase">
          {how.eyebrow}
        </p>
        <h2 className="mt-3 text-heading-2 text-ink">{how.heading}</h2>
      </div>

      <Grid cols={3} className="mt-10">
        {how.steps.map((step) => (
          <Card key={step.n} variant="base" className="p-6">
            <span className="flex size-9 items-center justify-center rounded-full bg-green-soft font-mono text-body-md-medium text-green-dark tabular-nums">
              {step.n}
            </span>
            <h3 className="mt-4 text-heading-4 text-ink">{step.title}</h3>
            <p className="mt-2 text-body-sm text-steel">{step.body}</p>
          </Card>
        ))}
      </Grid>
    </Section>
  );
}
