# P9.S4 — Plan: App surfaces (all six)

## Context — why this slice exists

The broadest slice: with tokens (S1), primitives (S2) and app components (S3) in place, S4 updates the
six shipped surfaces to compose them — auth, dashboard, project detail, feedback list, feedback detail —
plus the three island forms. Mostly class swaps + wiring the new Select/Chip/destructiveOutline/breadcrumb;
**no new capability, no backend**. Non-breaking (every primitive it uses already exists), so the tree
stays green.

Source of truth on disk (no DesignSync): `build-prompt.md §5` (per-file surface changes) + §4.2 (compact
density) + §4.8/§4.9 (Select/Chip adoption). Read `works/phases/active/P9/phase.md` first.

**Already done by earlier slices — do NOT redo:** `feedback-fields.tsx` (RatingBadge fully migrated, S2);
the credential **status badges** in `projects/[projectId]/page.tsx` (`active`/`revoked`, S2). S4 does the
*rest* of the project page.

## RESPECT THE DESIGN — the load-bearing constraint (verbatim; in every P9 plan + dispatch)

> Ship every designed element as designed — layout, density, hierarchy, tokens, interactions,
> empty/error/loading states. **Do not drop, simplify, restyle, or "improve" a designed element to save
> effort** — that is a correctness failure, not a shortcut. Where an exact value isn't specified, pick
> the option closest to the designed intent, **never a plainer fallback**. Where the design implies
> backend/data work, **build the backing** and surface the choice — don't quietly drop the feature.
> (This round implies **no** backend change; §9 confirms it.)

## The work (per file — §5 unless noted)

### `app/(auth)/auth-card.tsx`
Replace the `<p>{SITE.name}</p>` text brand with a centered **`<Mark/>` + `<Wordmark/>`** above the card
(from `@/components/brand`; use the larger mark — this is a brand moment). Keep `Card variant="feature"`
and the alt-link. Wrapper `max-w-[420px]` → **`max-w-[400px]`**. Drop the now-unused `SITE` import.
**Do NOT touch** the login/signup form logic or the identical-401-error mapping (in the forms/BFF — locked).

### `app/(app)/dashboard/page.tsx`
`space-y-8` → **`space-y-6`**. Project-name link → add `hover:text-green-dark` (→ `font-medium text-ink
hover:text-green-dark hover:underline`). Title already `text-heading-3`; StatTiles/TrendChart already
restyled (S3) — no change. Keep the two-parallel-calls data logic and `empty` copy verbatim.

### `app/(app)/dashboard/create-project-form.tsx`
Buttons already resolve to the restyled `primary` primitive — **likely no change**; verify only. No logic change.

### `app/(app)/projects/[projectId]/page.tsx`
Add the **breadcrumb** above `<h1>{project.name}`:
`<nav className="text-body-sm text-steel"><Link href="/dashboard" className="text-green-dark hover:underline">Dashboard</Link> / {project.name}</nav>`
(add the `Link` import). `space-y-8` → **`space-y-6`**. Status badges already `active`/`revoked` (S2) —
leave them. No breakpoint literals here.

### `app/(app)/projects/[projectId]/mint-credential-form.tsx`
`ShowOnceKey` panel → the **green-tinted card**: `rounded-lg border border-security-mint bg-surface-green p-4`
(was `border-hairline-strong bg-surface`). **Keep `PROJECT.keyPanel.warning` verbatim** (locked show-once
floor) and the Copy/Dismiss controls + all the dismissal/`ok`-stamp logic. Submit button stays `primary`.

### `app/(app)/projects/[projectId]/revoke-credential-button.tsx`
Both revoke buttons (the trigger and the confirm) → **`variant="destructiveOutline" size="sm"`**; the
cancel stays `variant="link"`. **Keep the two-step inline confirm + best-effort logic verbatim.** Rewrite
the stale doc comment (lines ~33–35: "the palette has no destructive button variant… P6 gate" is now false —
vocky ships `destructive`/`destructiveOutline`).

### `app/(app)/feedback/page.tsx`
- Swap the **two raw `<select className={inputVariants()}>`** (Project, Rating) for **`<Select>`** (§4.8):
  `<Select id name defaultValue …>{options}</Select>`. Drop the now-unused `inputVariants` import.
- Filter `Card variant="base"` — already. `space-y-8` → **`space-y-6`**.
- **Migrate `min-[900px]:` → `app:`** (the 4 FilterBar utilities: `flex-row`/`items-end`/`flex-1`/`w-56`/`w-40`).
- **Optional active-filter Chips: SKIP** (default). `build-prompt §5/§4.9` marks them *optional*, and this
  page is deliberately a **no-client-island GET form** (documented) — removable chips need client JS. Skipping
  is spec-compliant; if the operator wants them later they'd be **link-based** (server-friendly) as an S7
  fidelity add. Note this in `result.md`.
- **Keep verbatim (locked):** the plain `<form method="GET">`, the blank-is-absent param logic, forward-only
  `Next page`, and the two distinct empty states (`emptyNoProjects` vs `emptyNoMatches`).

### `app/(app)/feedback/[feedbackId]/page.tsx`
- **Tags → `<Chip>`** (§4.9): replace the bespoke `rounded-full … px-2.5 py-1` `<li>` span with
  `<li key={tag}><Chip>{tag}</Chip></li>` (import `Chip`). Keep the `tagsNone` empty case.
- **Migrate `min-[900px]:` → `app:`** (the `dl` grid `min-[900px]:grid-cols-3`). `space-y-8` → **`space-y-6`**.
- **Keep verbatim (locked):** the `dl` Details grid, the whitespace-preserving message/comment cards, the
  read-only operator comments, **download-only attachments** (the proxy `href` + `download` attr, never
  inline), and the collapsible Raw blocks.

## Breakpoint migration completes here

S4 migrates the remaining **7** `min-[900px]:` literals (feedback list ×4-ish, feedback detail ×1, and any
stragglers). Combined with S3's 4, **all 11 are gone** after S4 — S7 asserts zero remain. `--breakpoint-app`
(S1) makes `app:` resolve.

## Locked floors S4 must preserve

Identical login error (untouched — in forms/BFF); show-once `vk_` warning verbatim + revoked keys stay
listed; download-only attachments; UTC `Timestamp`s; distinct feedback empty states; the feedback list's
no-JS GET form + blank-is-absent + forward-only pagination; `word-break: keep-all` (global). None of these
change — only styling/wiring around them.

## Boundary — do NOT touch

`ui/` primitives (S2), app components / brand (S3), `globals.css`/`fonts.ts` (S1), `feedback-fields.tsx`
(S2 finished it), the net-new states (S5), or the landing (S6). No backend / `src/vocky/**` / `lib/vocky/*`
change (§9). Copy in `content/*` is locked — reuse existing strings, invent none.

## Verification

- `cd web && pnpm typecheck && pnpm lint` clean; **`cd web && pnpm build` green**.
- `prettier --write` the touched files only (avoid the 20 pre-existing unrelated `format:check` failures).
- Greps: **zero `min-[900px]:` anywhere in `src/`** (S3+S4 complete the migration); no
  `inputVariants()`-template `<select>` remains; `<Chip` used in feedback detail; `destructiveOutline` in
  the revoke button; `border-security-mint bg-surface-green` in the key panel; the breadcrumb `nav` in the
  project page.
- Smoke (if cheap): render `/login`, `/dashboard`, a `/projects/[id]`, `/feedback`, and a `/feedback/[id]` —
  the vocky palette, compact density, Select filters, Chip tags, breadcrumb, green key panel, and Korean
  content all render; the GET-form filters and forward-only pagination still work.

## Doc impact (append one line to `phase.md` → Doc impact; do NOT version docs here)

All six app surfaces rendered in the vocky system at compact density: Select filters, Chip tags, project
breadcrumb, destructiveOutline revoke, green-tinted show-once key panel; the `min-[900px]:`→`app:` migration
completed. `frontend.md` (v0003) still describes the placeholder surfaces. For `P9.REVIEW`.
