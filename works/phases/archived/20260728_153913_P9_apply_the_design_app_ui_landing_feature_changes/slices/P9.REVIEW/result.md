# P9.REVIEW — Result: phase review + durable-doc consolidation

**Verdict: `pass`.** P8's signed-off round-01 design is applied faithfully across the whole app
and the public landing. All consolidated validation is green, every `build-prompt.md §10` DoD item
holds, every locked floor survives, no backend/contract was reopened, and the one deliberate omission
is spec-sanctioned. On the pass I consolidated the phase's accumulated Doc-impact notes into two new
durable-doc versions (`frontend` v0004, `experience` v0007) and left `decisions` at v0006 (reasoning
below).

---

## 1. Consolidated validation (re-run as the phase gate)

| Command | Result |
|---|---|
| `cd web && pnpm typecheck` | ✅ clean (`tsc --noEmit`) |
| `cd web && pnpm lint` | ✅ clean (`eslint .`) |
| `cd web && pnpm build` | ✅ green — compiled successfully; 12 routes; `/` is `ƒ` (reads cookie), `/_not-found` static |
| `cd web && pnpm test` | ✅ **56/56** vitest (5 files) |
| `python3 scripts/workflow.py validate` | ✅ state integrity passed |
| `python3 scripts/workflow.py rebuild-docs` | ✅ regenerated `docs/current/*` |
| `python3 scripts/workflow.py validate` (post-docs) | ✅ passed |

**Negative-space grep invariants (all hold):**
- `min-[900px]:` → **0**; `--breakpoint-xs` → **0**; `--breakpoint-app` → **1** definition; `app:` variant → in use.
- Raw `inputVariants()`-template `<select>` → **0** (the only `inputVariants` hits are the `field.tsx`
  definition, the sanctioned `selectVariants = cva(cn(inputVariants(), …))` composition in `select.tsx`,
  and comments — no `<select className={inputVariants()}>` remains).
- Old variant names (`softGreen`, `secondaryOnDark`) → **0**; Card `security`/`archive` usage → **0**.
- `content/nav.ts` → **gone**; `NAV_LINKS` / `SKIP_TO_CONTENT` refs → **0**.

**Phase diff scope (`e3550c0..1e271bd`) — web + works only.** The whole P9 diff touches only `web/src`
and `works/*`. **No `src/vocky/**`, no `.py`, no alembic/pyproject/uv.lock** — confirms `build-prompt.md §9`
(no backend or P2/P3 contract change). The Pretendard asset is a vendored `web/src/lib/fonts/*.woff2`
(web-tier), no new npm dependency.

## 2. Review against objective / intent / DoD §10

**Objective met.** The deep-emerald names-kept value swap, the compact type/radius/spacing scale,
Pretendard (vendored via `next/font/local`), the new component vocabulary (Select, Chip,
destructive/destructiveOutline/ghost Button, split Badge, folded LogoutButton, dependency-free area
TrendChart, brand Mark/Wordmark), the `--breakpoint-app` migration, the four net-new states, and the
public `/` landing that bounces signed-in visitors — all shipped, foundation-first (S1) → primitives (S2)
→ app components + brand (S3) → app surfaces (S4) → net-new states (S5) → landing (S6) → DoD sweep (S7),
exactly the intent's expected shape. The design-fidelity fix folded into S7 needed **no** reactive
`--kind fix` slice (S1–S6 built to spec).

**All 12 DoD §10 items hold** (verified against the built app + each slice's `result.md`, cross-checked
against S7's item-by-item walk): §2/§3/§4 token values + updated header; Pretendard + Korean-capable
fallback + non-bare `--font-en`; `rounded-md` buttons + the three new variants + Button LogoutButton;
Select/Chip adopted with no `inputVariants()`-template `<select>`; split Badge with active/revoked +
liked/disliked/unrated; dependency-free area TrendChart + a11y summary + both empty shapes; six surfaces
at compact density + project-detail breadcrumb; `/` landing + signed-in bounce + copy from
`content/landing.ts`; the four states + generic 404; `--breakpoint-xs` gone + `--breakpoint-app` + no
`min-[900px]:`; every locked floor; no `src/vocky/**` change.

**RESPECT THE DESIGN held.** Every designed element shipped as designed — nothing dropped, simplified, or
"improved." The build-time judgment calls (Mark bar proportions, feature-card waveform accent, auth
wordmark size) are all "closest-to-designed-intent," never a plainer fallback. The **one deliberate
omission** — the feedback-list *optional* removable filter-chips — is **spec-sanctioned**
(`build-prompt.md §5/§4.9` mark them optional) and preserves the page's no-client-island GET-form design;
it is **not** a drift. If ever wanted, they'd be link-based (server-friendly), never the client
`removable` Chip.

**All locked floors intact:** identical login error (401 → one message, in the form/BFF — untouched);
404-never-403 (single-sourced `STATES.notFound.body`, "…isn't here — or isn't yours to see"); show-once
`vk_` key warning verbatim + green-tinted panel + revoked-stays-listed; download-only attachments; UTC
labels; `word-break: keep-all`; Korean-capable `--font-sans` (Pretendard, Noto Sans KR fallback);
`FieldError` `min-h-[1.25rem]` `aria-live="polite"`; two distinct empty states.

**Known pre-existing debt (not a blocker):** `pnpm format:check` fails on **13 P4-era**
backend/lib/test files (README, `actions.ts`, `lib/*`, `lib/vocky/*`, `tests/*`). **P9 introduced none** —
all P9-touched files are prettier-clean. A defer-job candidate for the orchestrator (out of P9's charter).

## 3. Verdict — `pass`

Objective met, DoD §10 fully holds, all locked floors survive, no backend/contract change, the diff is
web + works only, and the negative-space invariants are clean. No `changes_requested`, no blocker.

## 4. Doc consolidation (on the pass)

- **`frontend` v0003 → v0004** (`docs/versions/frontend/v0004_…placeholder_retired.md`). Flipped the doc
  from "live placeholder / P9 has not landed yet" to the **applied vocky brand**: deep-emerald names-kept
  value swap (all 41 token names kept, values swapped; the by-hand literal fixes; `on-primary` white); the
  compact type/radius/spacing scale; the `--breakpoint-app` migration (xs dropped, zero `min-[900px]:`);
  Pretendard via vendored `next/font/local` woff2; the new component vocabulary (Select, Chip, seven-variant
  Button, split Badge, brand Mark/Wordmark, area TrendChart, ghost LogoutButton, compact DataTable/Field);
  the public `/` landing + the four net-new states; the retired `content/nav.ts`/`section-ids`/`types`
  leftovers; and the applied-state inventory (breadcrumb, `active`/`revoked` badges, `destructiveOutline`
  revoke, green-tinted show-once panel, `<Select>` filters, `<Chip>` tags). Recorded the 13-file
  pre-existing format debt and the spec-sanctioned filter-chip omission. Durable BFF/session/mutations/
  client sections carried forward unchanged (P9 didn't touch them).
- **`experience` v0006 → v0007** (`docs/versions/experience/v0007_…real_product_surface.md`). Added a
  **"The landing page (`/`)"** subsection to *The Web App*: `/` is now a public marketing landing for
  signed-out visitors (server-to-server capture pitch, Start-free / Read-the-docs CTAs to the real repo),
  with the signed-in→`/dashboard` bounce preserved and no token exposed. The API/capture/read guide is
  otherwise unchanged (P9 was web-tier only).
- **`decisions` — left at v0006 (no new version).** D-P8-1 is **applied** by P9, **not superseded** — P9
  made no new decision (a faithful apply, no reactive fix slice, no scope change, no operator ruling). A
  pure "now applied" status-flip is exactly the status note the plan says not to version for; the
  applied-state durable truth lives in `frontend` v0004 + `experience` v0007, and D-P8-1 stands as the
  valid point-in-time record of the P8 gate. No other doc changed (§9: no backend/data/security/api/
  architecture/product/operations change; security floors preserved and already documented at `security`
  v0005).

`rebuild-docs` regenerated `docs/current/frontend.md` (v0004) + `docs/current/experience.md` (v0007);
`docs/current/decisions.md` stays v0006. Post-rebuild `validate` clean. `git status` shows only
`docs/*` + `works/*` from this slice — no source touched.

## 5. Deviations from `plan.md`

**None material.** Two notes: (a) the plan's Doc-impact preamble cited a "20" pre-existing format-debt
count; the reconciled figure is **13** (S7 verified — P9 introduced none either way). (b) I exercised the
plan's explicit judgment latitude on `decisions` and left it at v0006 (the plan's stated default when the
only change is a status note). Everything else followed the plan exactly.
