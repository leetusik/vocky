# P9.S7 — Result: Consistency & DoD sweep + design-fidelity fixes

**Verdict: done.** The whole app was walked against `build-prompt.md §10`, every DoD item holds,
zero drift fixes were needed (S1–S6 landed the design faithfully), the dead nav/section-id leftovers
were retired, and the full verification suite + a broad live-backend dev-server smoke are green. The
phase meets its objective.

---

## 1. DoD §10 walk — item by item

Every §10 checkbox was verified against the built app. All hold as designed; **no drift fix was
required** (this sweep confirmed S1–S6's fidelity rather than repairing it).

| # | §10 item | Result | Evidence |
|---|---|---|---|
| 1 | `globals.css` holds §2/§3/§4 values, no accidental duplicates, header comment updated | ✓ | Header comment rewritten to the vocky brand (no "PLACEHOLDER"); spot-checked tokens match §2.1 (`--color-ink #0e1a16`, `--color-green #0c7a52`, `--color-green-deep #095e40`, `--color-danger #c93b2b`, `--color-security-teal #2fa477`, `--color-surface-band #edf2ef` ≠ `--color-surface-soft #eef3f0`) |
| 2 | Pretendard loads (Korean renders) with a Korean-capable fallback; `--font-en` not a bare system stack | ✓ | `--font-sans` and `--font-en` both lead `var(--font-pretendard)`, keep `"Noto Sans KR"` in the chain; Korean renders in the live smoke (`결제 단계에서 카드가 자꾸 거절돼요.` on the landing + feedback detail) |
| 3 | Buttons `rounded-md`; `ghost`/`destructive`/`destructiveOutline` exist; LogoutButton is a `Button` | ✓ | `button.tsx` base is `…rounded-md…` verbatim §4.4; all seven variants present; `logout-button.tsx` renders `<Button variant="ghost" size="sm">` |
| 4 | `Select` + `Chip` exist and are used; no `inputVariants()`-template `<select>` remains | ✓ | `<Select>` ×2 in feedback FilterBar, `<Chip>` in feedback detail; zero raw `<select>` in `src/app`; the only `inputVariants()` hits are comments + the legitimate `selectVariants = cva(cn(inputVariants(), …))` composition (§4.8) |
| 5 | Badge `archive` split; credential status `active`/`revoked`; rating `liked`/`disliked`/`unrated` | ✓ | `badge.tsx` variants `liked/disliked/unrated/active/revoked/accent`, `defaultVariants {unrated}`; project detail uses `<Badge variant="active">` / `"revoked"`; feedback-fields `RatingBadge` uses the rating trio |
| 6 | TrendChart = dependency-free area redesign + a11y summary + both empty shapes | ✓ | `trend-chart.tsx` is the `viewBox 0 0 100 42` area chart (`<linearGradient>` + `role="img"` + `preserveAspectRatio="none"`), `sr-only` summary sentence kept, `days.length === 0` empty box + `Math.max(1, …)` floor for the all-zero flat line |
| 7 | All six app surfaces render the new system at compact density; project detail has a breadcrumb | ✓ | Live smoke rendered dashboard, project detail, feedback list, feedback detail, auth, landing; project detail shows the `<nav>` breadcrumb with the `Dashboard` link + `project.name` |
| 8 | `/` serves the landing to signed-out, bounces signed-in to `/dashboard`; landing copy from `content/landing.ts` | ✓ | Signed-out `GET /` → 200 landing; forged-valid cookie → 307 → `/dashboard`; `page.tsx` composes `LandingNav/main/LandingFooter` from `LANDING` |
| 9 | `loading`/`error`/`not-found`/`global-error` exist and match; 404 copy generic (404-never-403) | ✓ | All state files present; unknown URL → HTTP 404 with `"…isn't here — or isn't yours to see."` (single source in `STATES.notFound.body`) |
| 10 | `--breakpoint-xs` gone; `--breakpoint-app` used; no `min-[900px]:` literals remain | ✓ | grep: 0 `--breakpoint-xs`, 1 `--breakpoint-app` def, 0 `min-[900px]:`, 18 `app:` usages |
| 11 | Locked floors intact | ✓ | Identical 401 (`invalidCredentials` copy, in the BFF — untouched); 404-never-403; `PROJECT.keyPanel.warning` verbatim + green-tinted panel + revoked-stays-listed; download-only attachments (`download` attr on proxy href); UTC labels (`timeZone: "UTC"`); `word-break: keep-all`; Korean-capable `--font-sans`; `FieldError` `min-h-[1.25rem]` `aria-live="polite"`; two distinct empty states (`emptyNoProjects` vs `emptyNoMatches`) |
| 12 | No `src/vocky/**` change; all data maps to existing serializers | ✓ | S7 touched only `web/src/content/*`; no backend/lib edit. Live smoke round-tripped real data through the existing serializers unchanged |

## 2. Cross-slice consistency + fidelity spot-check (negative-space backstop)

All invariants already held (S1–S6 were faithful); S7 confirmed, no fix needed:

- `min-[900px]:` literals: **0** in `web/src/`.
- `--breakpoint-xs`: **0**. `--breakpoint-app`: **1** definition, **18** `app:` variant usages.
- `inputVariants()`-template raw `<select>`: **0** (only the sanctioned `selectVariants` cva reuse).
- Old variant names (`softGreen`, `secondaryOnDark`, Card `security`/`archive`): **0** usages.
- Fidelity spot-checks: button base `rounded-md` (§4.4 verbatim), §4.7 badge variant set exact,
  §2.1 token sample exact, landing composes the real adopted primitives.

## 3. Dead nav/section-id retirement (grep-confirmed safe, re-grepped after each deletion)

- **Deleted** `web/src/content/nav.ts` (`NAV_LINKS`, `SKIP_TO_CONTENT`, the `section()` helper) — only
  `content/index.ts` re-exported it; the landing uses its own nav from `LANDING.nav`.
- **`content/section-ids.ts`**: removed the dead `overview`/`primitives` ids (and their stale comment);
  `SECTION_IDS` now holds only the live landing anchors `features`/`how`/`pricing`. The `SectionId`
  type is intact (still consumed by `ui/section.tsx` + `content/landing.ts`).
- **`content/index.ts`**: dropped `export { NAV_LINKS, SKIP_TO_CONTENT } from "./nav"` and trimmed the
  type re-export to `export type { SiteMeta } from "./types"`.
- **`content/types.ts`**: `NavLink`, `Cta`, and the `sectionId` field became fully unused after the
  above (grep-confirmed) and were removed, along with the now-unneeded `SectionId` import/re-export;
  `types.ts` now holds only `SiteMeta`.
- **Post-deletion re-grep (all clean):** `nav.ts` gone; 0 refs to `NAV_LINKS`/`SKIP_TO_CONTENT`/
  `NavLink`/`Cta`/`sectionId`/`./nav`/`SECTION_IDS.overview`/`SECTION_IDS.primitives`.

## 4. Verification

| Command | Result |
|---|---|
| `pnpm typecheck` | ✅ clean (`tsc --noEmit`) |
| `pnpm lint` | ✅ clean (`eslint .`) |
| `pnpm build` | ✅ green — 12 routes compile; `/` is `ƒ` (reads cookie), `/_not-found` `○` static |
| `pnpm test` | ✅ **56/56** vitest pass (5 files) — no backend/lib regression |
| `prettier --write` (touched files) | `section-ids.ts` / `index.ts` / `types.ts` all clean (unchanged) |
| `python3 scripts/workflow.py validate` | ✅ workflow validation passed |

### Dev-server smoke (live backend on `127.0.0.1:8000`, real signup → project → key → feedback)

Every requested surface exercised against the running app + backend:

| Surface | Session | Result |
|---|---|---|
| `/` | signed-out | 200, landing markers present (headline + `#main-content`) |
| `/` | forged-valid cookie | 307 → `/dashboard` (signed-in bounce) |
| `/` | tampered cookie | 200 signed-out, no crash |
| `/login` | — | 200, vocky wordmark |
| `/dashboard` | live | 200, app shell + wordmark (fresh empty state) |
| `/projects/[id]` | live (real project) | 200 — breadcrumb `Dashboard` link + `Smoke Project` name + credential status badges |
| `/feedback` | live | 200 — empty state, then populated after seeding (Korean row) |
| `/feedback?feedback_value=2` | live | 200 — disliked record shows |
| `/feedback?feedback_value=1` | live | 200 — record excluded, empty-no-matches state |
| `/feedback?q=checkout` | live | 200 — substring match shows the record |
| `/feedback/[id]` | live (real record) | 200 — Korean message rendered, `<Chip>` tags, UTC labels |
| `/dashboard`, `/feedback` | no session | 307 → `/login` (auth guard) |
| `/this-does-not-exist-xyz` | — | 404 with the 404-never-403 copy (not the framework default) |

Seeded data was created purely through the backend's existing public API (`POST /api/feedback` with a
minted `vk_` key, Bearer auth, nested `source` per `src/vocky/smoke.py`) — no backend code was changed.

## 5. Pre-existing format debt — flagged, NOT fixed

`pnpm format:check` fails on **13** P4-era files, none P9-owned — a defer-job candidate for the
orchestrator:

```
README.md
src/app/(app)/dashboard/actions.ts
src/app/(app)/projects/[projectId]/actions.ts
src/lib/bff.ts
src/lib/env.ts
src/lib/session.ts
src/lib/vocky/auth.ts
src/lib/vocky/types.ts
tests/auth-routes.test.ts
tests/session-guards.test.ts
tests/session.test.ts
tests/vocky-app.test.ts
tests/vocky-auth.test.ts
```

**P9 introduced zero format debt** — all P9-touched files (including S7's three content edits) are
prettier-clean. Note: earlier slices' notes cited "20" pre-existing failures; the current count is
**13**. The reduction is consistent with earlier P9 slices running `prettier --write` on files they
legitimately touched that happened to be in the original failing set (e.g. `content/index.ts`,
`globals.css`) — i.e. incidental cleanup of files P9 owned, never a reformat of the out-of-scope P4
backend/lib/test files above, which are left untouched. Reformatting those 13 stays out of P9's charter.

## 6. Does the phase meet its objective?

**Yes.** P8's signed-off round-01 design is applied faithfully across the whole app and the public
landing: the deep-emerald `@theme` value swap, the compact type/radius/spacing retune, Pretendard, the
new component vocabulary (Select, Chip, destructive/destructiveOutline/ghost Button, split Badge, folded
LogoutButton, area TrendChart), the four net-new states, the `--breakpoint-app` migration, and the
public `/` landing that bounces signed-in visitors. Every §10 DoD item holds, every locked floor
survives, no backend contract was reopened (§9), and the dead S1-preview leftovers are retired. The
sweep found **no drift to fix** — S1–S6 built to spec — so no reactive `--kind fix` slice was needed.
`P9.REVIEW` is the remaining gate; it validates all slices together and consolidates the accumulated
Doc-impact notes into `frontend.md` / `experience.md` / `decisions.md` versions.

## Deviations from `plan.md`

**None.** The DoD walk surfaced no drift (the plan anticipated "few or none"), so S7 made only the
planned dead-content retirement plus its `result.md`/`phase.md` writes. The two nuances worth recording:
(a) the pre-existing format-debt count is **13**, not the 20 the plan cited (reconciled above — P9 still
introduced none); (b) the smoke was run against a **live backend** with real seeded data (fuller than a
routing-only smoke), which strengthened rather than reduced coverage.
