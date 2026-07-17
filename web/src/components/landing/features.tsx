import { Card, Grid, Section } from "@/components/ui";
import { LANDING } from "@/content";

// Features (P9.S6, build-prompt §7.3). Six real capabilities in a `Grid cols={3}`
// of cards — every claim grounded in the actual product (server-to-server
// capture, structured records, cross-language search, per-project `vk_` keys,
// explicit-only signal, MIT + self-hostable). Anchored `#features` for the nav.
// Each card leads with a small green waveform accent (three rising bars, the
// brand motif) so the grid reads as vocky, not generic marketing.

const { features } = LANDING;

export function Features() {
  return (
    <Section id="features" tone="surface" reveal>
      <div className="max-w-2xl">
        <p className="text-caption font-semibold tracking-[0.12em] text-green-dark uppercase">
          {features.eyebrow}
        </p>
        <h2 className="mt-3 text-heading-2 text-ink">{features.heading}</h2>
      </div>

      <Grid cols={3} className="mt-10">
        {features.items.map((item) => (
          <Card key={item.title} variant="base" className="p-6">
            <span
              aria-hidden="true"
              className="flex h-9 w-9 items-end justify-center gap-[3px] rounded-md bg-green-soft p-2"
            >
              <span
                className="w-[3px] rounded-full bg-green"
                style={{ height: "40%" }}
              />
              <span
                className="w-[3px] rounded-full bg-green"
                style={{ height: "70%" }}
              />
              <span
                className="w-[3px] rounded-full bg-green"
                style={{ height: "100%" }}
              />
            </span>
            <h3 className="mt-4 text-heading-4 text-ink">{item.title}</h3>
            <p className="mt-2 text-body-sm text-steel">{item.body}</p>
          </Card>
        ))}
      </Grid>
    </Section>
  );
}
