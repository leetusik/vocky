# P4.REVIEW — Plan: Phase review + durable-doc consolidation

Orchestrator's native plan for slice **P4.REVIEW** (`kind: review` → executed by **`slice-executor-high`**, which the contract mandates for review regardless of the `medium` risk rating). The phase's last slice.

## Context

P4 stood up vocky's **first frontend**: a Next.js app in `web/` (design system → auth/BFF → dashboard → project detail → feedback search) that replaces the packaged operator admin UI as the browser surface. All five middle slices + `DECOMP` are `done` and committed (`b9b0f2f` → `d816a01`); `P4.REVIEW` is the only slice left.

This slice does the two things no individual slice could: **judge the phase as a whole**, and **consolidate `phase.md`'s six per-slice "Doc impact" notes into durable doc versions** (the one point in the phase where `doc-new-version` may run).

Each slice already drove its own live E2E and returned a trusted `done`. So this review is **not** a re-run of ~40 per-slice assertions. Its unique value is the composed whole: every slice proved *its own surface in isolation*, and **nobody has yet walked the entire app as one user in one session**.

**A rubber stamp is the failure mode here.** The slices were verified well and a `pass` is the likely outcome — but reach it by looking, not by assuming.

## Already verified by the orchestrator (don't redo)
- `python3 scripts/workflow.py validate` — passes; all 5 middle slices + `DECOMP` are `done`, `REVIEW` is `todo`.
- **No `src/vocky/**` edits anywhere in P4** (`git diff --name-only b9b0f2f~1..HEAD -- src/vocky/` is empty) — the "no backend change" constraint held across the phase.
- **The app never calls the `vk_`-keyed `/api/*` surface** (grep of `web/src` for `getJson`/`sendJson`/`getRaw` against `/api/…` is clean). Note `web/src/app/api/**` is the app's *own* BFF routes on the Next origin — not vocky's `/api/*`; don't confuse them.
- S5's `web/.env.local` is gitignored and untracked; no `.env.local` or `tsbuildinfo` was ever committed.
- The stale `rail-nav.tsx` comment S5 flagged (but was forbidden to touch) is **already fixed** in `d816a01`.

## 1. Validate all slices together

One consolidated gate — the slices' commands are identical and the later suites subsume the earlier:
```
cd web && pnpm install --frozen-lockfile && pnpm typecheck && pnpm lint && pnpm test && pnpm build
python3 scripts/workflow.py validate      # from the repo root
```
Expect **56/56 tests**, all routes `ƒ (Dynamic)`, and an action manifest of **exactly 3**. A cross-slice regression here (e.g. a late slice breaking an early slice's suite) is a `changes_requested`.

## 2. The composed live walk (this review's unique check)

vocky is healthy on `:8000` and the worker is current (fresh captures persist with `project_id`). **Run web on `pnpm dev`, never `pnpm start`** — the prod build marks the session cookie `Secure` and a plain-http client silently never replays it, bouncing every guarded page to `/login` (this cost S4 a wasted run; S5 confirmed the workaround).

Walk the whole app **as one user in one continuous session**, which no slice did:

> signup → land in the shell → dashboard (create a project) → follow the project link → project detail (mint a `vk_` key) → capture feedback with that key, including Korean → rail to `/feedback` → search `?q=결제` → open the record's detail.

The point is **composition**, not re-testing each surface: the S2 session carries S3's fetches; S3's link lands on S4's route; S4's minted key produces the data S5 renders. That chain is what P4 promised and what no slice tested.

Also confirm at the seams: the rail's active state is right across all routes, `/feedback` is a real link (no "Soon" tag), and a signed-out user hitting any `(app)` route bounces to `/login`.

Spot-check the phase's cross-cutting constraints (`phase.md` § Constraints) rather than re-proving each slice's own list — most notably **404-never-403 on a foreign id**, **no vocky token or `vk_` string in any rendered HTML**, and **no dark-mode toggle**.

If the live walk is genuinely blocked, complete §1, capture the exact failing command + error, and return **`blocked`** (not a `pass` with a caveat). **Never claim a walk you didn't drive.**

## 3. Review against objective, intent, and docs

Judge P4 against `phase.md` § Objective, `intent.md` § Confirmed Intent, and § Constraints. The core question: *is the authenticated web app — tenant dashboard + project detail — really built, hi2vi_web-style, as the replacement browser surface?*

Adjudicate the phase's accumulated deviations (all recorded in `phase.md`; confirm each was sound and is honestly recorded):
- **S3 dropped `GET /app/tenant`** from the DECOMP sketch (the shell already has the tenant from a `cache()`d `/auth/me`).
- **No `listCredentials`** (S4 renders credentials from the usage payload by design).
- **S5** added a 5th file (`feedback-fields.tsx`), extended the 400/404→`notFound()` policy to the list page, mapped the proxy's vocky 401→401, and pinned timestamps to UTC.
- The **`soon` nav mechanism is deliberately retained** with zero call sites (documented, P6-facing). Confirm that's still the right call, or say so if not.

Also confirm the still-open items are correctly parked, not silently dropped: **admin-UI removal → P6**, **brand palette → P6 design gate**, **deploy → P6**, and **deferred job D2 stays deferred** (the dashboard is owner/session-scoped, so full-field exposure is appropriate).

## 4. Consolidate the docs — **only on a passing review**

Write **only** docs; never source. Use `python3 scripts/workflow.py doc-new-version --doc <doc> --summary "..." --source P4.REVIEW`, never hand-editing `docs/current/*.md` (generated snapshots).

**Order matters — P4 lands *on top of* P7.** The phases ran out of numeric order: `P7.REVIEW` already consolidated at **v0005** for `architecture`/`experience`/`product`. Each new version must **build on the current content, not revert it** — P7's MCP write-only capture surface stays exactly as it is. Read `docs/current/<doc>.md` before authoring each one.

| Doc | Next | Scope |
| --- | --- | --- |
| `frontend.md` | **v0002 — authored fresh** | Today a **363-byte bootstrap stub**. The phase's biggest doc job: the ported design system (`@theme` tokens, `cn`, CVA primitives + the net-new `data-table`), the `web/` structure, the BFF/session model, and the page/component inventory across S1–S5. |
| `architecture.md` | v0006 | The `web/` Next.js app + server-side BFF as vocky's browser surface (sealed httpOnly cookie, no CORS, no web-side DB); server actions for authed mutations vs BFF routes for the public auth surface; the binary attachment proxy + forced-download rationale. **Resolve the open question at `architecture.md:73`** — it currently reads *"reshaping this operator surface is deferred to P4"*, which P4 has now answered: the replacement is **built** in P4, physical removal of `admin_ui.py`/`admin_assets/*` is **deferred to P6**. |
| `experience.md` | v0006 | Signup/login/logout, the shell, the tenant dashboard, project drill-down + mint/revoke, and feedback search/read (downloads, not inline). |
| `decisions.md` | v0005 | **D-P4-1** (subdir `web/`), **D-P4-2** (BFF + sealed cookie, no CORS/DB), **D-P4-3** (port the design system, build functional, defer the heavy design gate to P6). |
| `operations.md` | **v0002** | Also a stub today. The web app build/run: `pnpm dev`, `output: "standalone"`, and the two **server-only** env keys (`VOCKY_API_BASE_URL`, `SESSION_SECRET` — neither `NEXT_PUBLIC_`). Production deploy stays **P6**. |
| `product.md` | v0006 — **judgment call** | `phase.md` marks this "possibly". Author it only if there's a real product-level fact to state (the authenticated web app becoming the primary user surface, per `intent.md`'s "the packaged admin UI retires — this app replaces it"). **If it adds nothing, skip it and say why** — don't mint an empty version. |

**A gap in `phase.md`'s Doc impact list — evaluate it, don't just follow the list.** The list omits **`security.md`** (currently v0004, backend-focused), yet P4 introduced real durable security truth: the **AES-256-GCM sealed httpOnly cookie** as the browser's credential, the BFF meaning **the vocky token never reaches browser JS**, the rate-limited public auth routes, the **show-once plaintext `vk_` key**'s single deliberate server→client crossing, and the proxy's **forced `Content-Disposition: attachment`** (uploader-supplied content declaring `text/html` served inline from our origin would be stored XSS; `nosniff` doesn't save you there). My lean: **`security.md` v0005 is warranted** — someone auditing vocky's credential handling looks there, not in `frontend.md`. Decide and record your reasoning either way.

## Executor guardrails
- **You MAY run `doc-new-version`** — this is the review slice, the one place it's allowed. **Docs only, never source.**
- **No commits. No slice/phase status transitions** — `review-phase` is the orchestrator's, and it closes the `REVIEW` slice itself.
- Write `works/phases/active/P4/slices/P4.REVIEW/result.md` (free-form) and return a **`review_verdict`**:
  - **`pass`** — the gate is green, the walk composed, the objective/intent are met, and the docs are consolidated.
  - **`changes_requested`** — something real is wrong. Propose concrete `P4.F<n>` fix slices. Docs are **not** consolidated (the next passing review does it).
  - **`blocked`** — you cannot complete the review (e.g. the live walk is impossible). Say exactly what's needed.
