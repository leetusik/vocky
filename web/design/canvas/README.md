# vocky design canvas

A standalone, browser-openable mirror of the vocky web app's design system. Each
card is a plain HTML file that `<link>`s a single shared token file
(`tokens.css`), so the whole canvas re-themes from one place. This is the
scaffold (P4.S1) of the design-gate mechanism; the **intensive operator design
session that turns the placeholder palette into the real vocky brand is deferred
to P6**.

## What's here

- **`tokens.css`** — the heart of the canvas. A 1:1 `:root` mirror of the app's
  `@theme` block in `web/src/app/globals.css`, expressed as plain CSS custom
  properties (same names, same grouping) so any browser renders the cards in the
  true palette + type. Fonts come from Google Fonts (`@import`) since the canvas
  is a standalone artifact, not under the app CSP — no woff2 is vendored here.
- **`_ds_manifest.json`** — machine-readable index: `namespace`, the mirrored
  `tokens[]`, `fonts[]`, and the `cards[]` list.
- **`foundations/`** — `colors.html`, `type.html`, `spacing-radius.html`.
- **`components/`** — `button`, `card`, `badge`, `field`, `grid`, `section`.
- **`sections/`** — `dashboard-placeholder.html` (a single placeholder card; real
  data-backed surfaces are designed at P6).

Every card's first line is a `<!-- @dsCard group="…" name="…" -->` marker so a
tool can discover + group the specimens.

## Placeholder palette

The values here are a **neutral placeholder set** — a slate surface ramp, one
indigo accent (the `green*` token group, hi2vi-compatible names), and standard
red/amber signal states. The token **names** are ported 1:1 from hi2vi_web, so
the P6 design gate swaps values only (in both `tokens.css` and the app's
`globals.css`), leaving the primitives and page classes untouched.

## Sync direction (canvas ↔ repo)

`tokens.css` is a *mirror* of the app's `@theme`. When the palette changes at P6,
edit both in lockstep: the app's `globals.css` `@theme` is the source of truth
for the running app; this `tokens.css` keeps the canvas faithful. Keep the names
identical so a diff is a pure value swap.

## Canvas ↔ repo mapping

| Canvas card                              | Repo source                                   |
| ---------------------------------------- | --------------------------------------------- |
| `tokens.css`                             | `web/src/app/globals.css` (`@theme` block)    |
| `foundations/colors.html`                | `@theme` color tokens                         |
| `foundations/type.html`                  | `@theme` `--text-*` scale                     |
| `foundations/spacing-radius.html`        | `@theme` `--spacing-*` / `--radius-*`         |
| `components/button.html`                 | `web/src/components/ui/button.tsx`            |
| `components/card.html`                   | `web/src/components/ui/card.tsx`              |
| `components/badge.html`                  | `web/src/components/ui/badge.tsx`             |
| `components/field.html`                  | `web/src/components/ui/field.tsx`             |
| `components/grid.html`                   | `web/src/components/ui/grid.tsx`              |
| `components/section.html`                | `web/src/components/ui/section.tsx`           |
| `sections/dashboard-placeholder.html`    | P4.S3 tenant dashboard (uses `data-table.tsx`)|

> Note: the `data-table` primitive (`web/src/components/ui/data-table.tsx`) is
> net-new in P4.S1 and has no standalone component card yet — it is previewed
> inside `sections/dashboard-placeholder.html`. A dedicated card can be added at
> the P6 session.
