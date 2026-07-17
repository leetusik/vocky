# P9.S4 — Result: App surfaces (all six)

**Verdict:** done. All six app surfaces (+ the three island forms) now compose the
vocky system (S1 tokens, S2 primitives, S3 app components) at compact density.
No new capability, no backend change — class swaps + wiring of the already-built
`Select` / `Chip` / `destructiveOutline` / brand-lockup / breadcrumb. The tree
stays green (typecheck / lint / build all clean).

## Per-file summary

### `app/(auth)/auth-card.tsx`
- Replaced the `<p>{SITE.name}</p>` text brand with a **centered brand lockup**:
  `<Mark size={52} />` + `<Wordmark className="text-[28px]" />` in a
  `flex items-center justify-center gap-3` row above the card. Used the larger
  (52px) mark per the plan ("brand moment"); scaled the wordmark to `text-[28px]`
  via the Wordmark's documented `className` size affordance (proportional to the
  larger mark, not a plainer default).
- Wrapper `max-w-[420px]` → `max-w-[400px]`. Dropped the now-unused `SITE` import
  (kept the `AuthPageCopy` type import). Card stays `variant="feature"`.
- Refreshed the stale component doc comment (it still claimed "the real design
  lands at the P6 gate; this is token-only") — the design has now landed.
- Login/signup form logic + the identical-401-error mapping (in the forms/BFF) —
  **untouched** (locked floor).

### `app/(app)/dashboard/page.tsx`
- `space-y-8` → `space-y-6`; project-name link
  `font-medium text-ink hover:underline` → `... hover:text-green-dark hover:underline`.
- StatTiles / TrendChart / data logic / copy — unchanged.

### `app/(app)/dashboard/create-project-form.tsx`
- **No change** — its submit `<Button variant="primary">` already resolves to the
  restyled S2 primitive. Verified only.

### `app/(app)/projects/[projectId]/page.tsx`
- Added `import Link from "next/link";` and the **breadcrumb** above the h1:
  `<nav className="text-body-sm text-steel"><Link href="/dashboard" …>Dashboard</Link> / {project.name}</nav>`
  (reuses the already-loaded `project.name`; no extra fetch, no rail-current change).
  Gave the h1 `mt-1` so the breadcrumb sits above it with tight spacing.
- `space-y-8` → `space-y-6`. Credential status badges already `active`/`revoked`
  (S2) — left as-is.

### `app/(app)/projects/[projectId]/mint-credential-form.tsx`
- Green-tinted the `ShowOnceKey` panel: `border-hairline-strong bg-surface` →
  **`border-security-mint bg-surface-green`** (kept `rounded-lg … p-4`).
- `PROJECT.keyPanel.warning` kept **verbatim**; Copy/Dismiss controls + the
  `ok`-stamp dismissal logic (the locked show-once floor) — untouched.

### `app/(app)/projects/[projectId]/revoke-credential-button.tsx`
- Both revoke buttons (the trigger and the confirm) → **`variant="destructiveOutline"
  size="sm"`**; cancel stays `variant="link"`.
- Two-step inline confirm + best-effort action logic — untouched (verbatim).
- Rewrote the stale doc comment ("the palette has no `destructive` button variant…
  the P6 design gate can swap values only") — vocky now ships `destructive` +
  `destructiveOutline`, so the note is obsolete.

### `app/(app)/feedback/page.tsx`
- Swapped the **two raw `<select className={`${inputVariants()} …`}>`** (Project,
  Rating) for `<Select>` (§4.8). The margin between Label and control moved to
  `wrapperClassName="mt-1.5"` (the Select's outer element is the positioning
  `<span>`; its `className` targets the inner `<select>` and it already applies
  `selectVariants()` = `inputVariants()` + chevron). Dropped the now-unused
  `inputVariants` import.
- `space-y-8` → `space-y-6`. Migrated the 4 FilterBar breakpoint literals
  `min-[900px]:` → `app:` (`flex-row`/`items-end`/`flex-1`/`w-56`/`w-40`).
- **Kept verbatim (locked):** the `<form method="GET">`, the blank-is-absent param
  logic, the forward-only `Next page` link, and the two distinct empty states
  (`emptyNoProjects` vs `emptyNoMatches`).

### `app/(app)/feedback/[feedbackId]/page.tsx`
- Tags: replaced the bespoke `rounded-full … px-2.5 py-1` `<li>` span with
  `<li key={tag}><Chip>{tag}</Chip></li>` (imported `Chip`). Kept the `tagsNone`
  empty case.
- `space-y-8` → `space-y-6`; migrated the `dl` grid `min-[900px]:grid-cols-3` →
  `app:grid-cols-3`.
- **Kept verbatim (locked):** the `dl` Details grid, whitespace-preserving
  message/comment cards, read-only operator comments, **download-only attachments**
  (proxy `href` + `download` attr, never inline), and the collapsible Raw blocks.

## Filter-chip skip decision (spec-optional) — SKIPPED, per plan

The build-prompt marks active-filter `Chip variant="filter"` pills on the feedback
list as **optional** (§5 "Optionally render active filters…"; §4.9 "optionally,
active-filter pills"). I did **not** add them. Rationale (from the plan, confirmed
against the code): the feedback list is a deliberate **no-client-island GET form** —
a server component with zero client JS (documented in its header comment). A
*removable* filter chip (`Chip removable onRemove`) requires a client parent to
supply `onRemove`, which would break that no-JS invariant. Skipping is
spec-compliant (the design contract itself marks it optional), and is **not** a
"plainer fallback" of a required element. If the operator later wants active-filter
pills, the server-friendly form is **link-based** chips (each linking to the same
filter set minus one param — no client JS) as an S7 fidelity add; noting here so
the decision is visible to the review.

## Breakpoint migration — COMPLETE after S4

S3 migrated 4 literals (app-shell ×2, rail-nav ×2); S4 migrated the remaining 5
(feedback list ×4, feedback detail ×1). **Zero `min-[900px]:` now remain anywhere
in `web/src/`** (grep-verified). `--breakpoint-app` (S1) resolves `app:`. S7's DoD
backstop should now find nothing to migrate.

## Verification

| Command | Result |
|---|---|
| `cd web && pnpm typecheck` | **PASS** (clean) |
| `cd web && pnpm lint` | **PASS** (clean) |
| `cd web && pnpm build` | **GREEN** — compiled + type-checked + all 7 static pages generated; all 12 routes present |
| `prettier --write` (8 touched files only) | applied; the 20 pre-existing unrelated `format:check` failures left untouched |

Grep-asserts (all PASS):
- zero `min-[900px]:` in `src/` — none
- no `inputVariants()` in `feedback/page.tsx` / no `inputVariants()` template `<select>` in `src/` — none
- `<Chip` in feedback detail — present
- `variant="destructiveOutline"` in revoke button — both buttons
- `border-security-mint bg-surface-green` in the key panel — present
- breadcrumb `<nav>` + `Link` import in the project page — present

Note: prettier reordered some non-conflicting Tailwind utility classes on lines
within the touched files (e.g. `whitespace-pre-wrap break-words` →
`break-words whitespace-pre-wrap`) — cosmetic class-sort only, no behavior change;
typecheck/lint stayed clean afterward.

## Notes for S5 / S7

- **S5 (net-new states):** the feedback list is a no-client-island GET form — keep
  its `loading` skeleton static/server-safe; nothing on it depends on client state.
  The project-detail page now leads with a breadcrumb `<nav>` then the h1 — if a
  `projects/[projectId]/loading.tsx` skeletons the header, mirror that order.
- **S7 (DoD sweep / fidelity):**
  - The `min-[900px]:` → `app:` migration is **fully done** (zero remain) — S7's
    backstop grep should pass without work.
  - The **filter-chip skip** above is the one deliberate spec-optional omission on
    these six surfaces; if S7 (or the operator) wants list active-filter pills, do
    them **link-based** (server-friendly), not with the client `removable` Chip.
  - Auth-card wordmark size (`text-[28px]`) and the 52px mark pairing are a
    build-time balance call for the "brand moment" — eyeball at review; the mark
    geometry itself is S3's (unchanged here).
  - `content/nav.ts` / `section-ids.ts` retirement is still S7's call — S4 did not
    touch them (feedback breadcrumb uses an inline literal "Dashboard" per the
    design contract §5, not a nav-content lookup).
