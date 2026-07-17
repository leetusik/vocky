import { Badge, Section } from "@/components/ui";
import { LANDING } from "@/content";

// Showcase — "One place to look" (P9.S6, build-prompt §7.3). A browser-framed
// mock of the real feedback list: the app's own When / Project / Feedback /
// Rating columns, rows carrying rating badges, Korean and English side by side.
// The window chrome + address pill are decorative (a `<span>`, never a link — no
// fake domain to 404). Korean cells carry `break-keep`. `<Section reveal>` for the
// one-shot scroll reveal.

const { showcase } = LANDING;

export function Showcase() {
  return (
    <Section tone="default" reveal>
      <div className="max-w-2xl">
        <p className="text-caption font-semibold tracking-[0.12em] text-green-dark uppercase">
          {showcase.eyebrow}
        </p>
        <h2 className="mt-3 text-heading-2 text-ink">{showcase.heading}</h2>
      </div>

      {/* Browser frame — decorative chrome, not interactive. */}
      <div className="mt-10 overflow-hidden rounded-xl border border-hairline bg-canvas shadow-[0_28px_64px_-32px_rgba(14,26,22,0.22)]">
        <div className="flex items-center gap-2 border-b border-hairline bg-surface px-4 py-3">
          <span
            aria-hidden="true"
            className="size-2.5 rounded-full bg-hairline-strong"
          />
          <span
            aria-hidden="true"
            className="size-2.5 rounded-full bg-hairline-strong"
          />
          <span
            aria-hidden="true"
            className="size-2.5 rounded-full bg-hairline-strong"
          />
          <span className="ml-3 rounded-md border border-hairline bg-canvas px-3 py-1 font-mono text-caption text-steel">
            {showcase.frame}
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[560px] border-collapse text-left">
            <thead>
              <tr className="border-b border-hairline">
                <th className="px-5 py-2.5 text-micro text-steel uppercase">
                  {showcase.columns.when}
                </th>
                <th className="px-5 py-2.5 text-micro text-steel uppercase">
                  {showcase.columns.project}
                </th>
                <th className="px-5 py-2.5 text-micro text-steel uppercase">
                  {showcase.columns.message}
                </th>
                <th className="px-5 py-2.5 text-right text-micro text-steel uppercase">
                  {showcase.columns.rating}
                </th>
              </tr>
            </thead>
            <tbody>
              {showcase.rows.map((row, i) => (
                <tr
                  key={i}
                  className="border-b border-hairline-soft last:border-b-0"
                >
                  <td className="px-5 py-3 font-mono text-body-sm whitespace-nowrap text-steel tabular-nums">
                    {row.when}
                  </td>
                  <td className="px-5 py-3 font-mono text-body-sm whitespace-nowrap text-slate">
                    {row.project}
                  </td>
                  <td className="px-5 py-3 text-body-sm break-keep text-slate">
                    {row.message}
                  </td>
                  <td className="px-5 py-3 text-right">
                    <Badge variant={row.rating}>{row.ratingLabel}</Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </Section>
  );
}
