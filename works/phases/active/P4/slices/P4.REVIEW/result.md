# P4.REVIEW — Result: phase review + durable-doc consolidation

**Verdict: `pass`.** The gate is green, the composed walk holds end-to-end, the objective and intent are met, and the phase's durable docs are consolidated into **8 versions**.

I reached `pass` by looking, not by assuming — the plan named a rubber stamp as the failure mode. What follows is what I actually drove, including the one thing I changed my mind about (two extra doc versions the Doc impact list did not name).

---

## 1. Consolidated gate — green

Run from `web/` unless noted. One gate for all five slices (their commands are identical; the later suites subsume the earlier).

| Command | Outcome |
| --- | --- |
| `pnpm install --frozen-lockfile` | **pass** — no lockfile change |
| `pnpm typecheck` | **pass** — clean |
| `pnpm lint` | **pass** — clean |
| `pnpm test` | **pass** — **56/56**, 5 files |
| `pnpm build` | **pass** — every real route `ƒ (Dynamic)`; only `/_not-found` is static (expected) |
| server-action manifest | **pass** — **exactly 3**: 1 × dashboard, 2 × project (mint + revoke). S5 added none. |
| `python3 scripts/workflow.py validate` (repo root) | **pass** |

**No cross-slice regression** — no late slice broke an earlier slice's suite.

Also confirmed independently of the slices' own claims:
- **`src/vocky/**` untouched across the entire phase** — `git diff --name-only b9b0f2f~1..HEAD -- src/vocky/` is empty. The "no backend change" constraint held.
- **Hygiene**: neither `web/.env.local` nor `tsconfig.tsbuildinfo` is tracked; both are correctly gitignored.
- **Dev log**: **0** 500s, unhandled errors, `TypeError`/`ReferenceError` across the whole walk.

## 2. The composed live walk — 44/44 (this review's unique check)

Every slice proved its own surface in isolation; **nobody had walked the whole app as one user in one session**. That is what I drove — `pnpm dev` on `:3030` (never `pnpm start`) against live vocky on `:8000`, worker current.

**The chain, in one continuous session:** signed-out bounce → signup → shell → dashboard → create project → **follow the dashboard's own link** → project detail → mint `vk_` → **capture Korean feedback with that minted key** → rail to `/feedback` → `?q=결제` → open the record's detail.

The composition is the point, and it holds: **S2's session carries S3's fetches; S3's link lands on S4's route; S4's minted key produces the data S5 renders.**

Highlights (44 assertions, all passing):

- **Signed-out**: all four `(app)` routes + `/` → `307 → /login`.
- **Signup** → `200` + sealed `v1.<iv>.<ct>.<tag>` cookie; shell renders the real identity.
- **Handoff (S3→S4)**: the dashboard renders **exactly one** `/projects/{uuid}` link and it lands `200`.
- **Show-once key**: exactly 1 distinct `vk_` at mint; **after reload the plaintext is gone**, no full key of any length remains.
- **The minted key really works**: 3 captures (2 Korean, 1 English) → `202`, persisted with `project_id`, and they appear on `/feedback`.
- **The flagship**: `?q=결제` matches the plain stem **and** the 조사-attached `결제를 못 했습니다`, and **excludes** the English row.
- **The blank-param submit** `?q=&project_id=&feedback_value=` (exactly what an empty GET form produces) → **200**, not vocky's 400.
- **Detail**: renders the Korean message + project name; **0 `<form>` elements** — read-only is structural.
- **Rail across all routes**: Dashboard current on `/dashboard`; Feedback current on `/feedback` **and** on `/feedback/[id]` (the `startsWith` prefix rule); `/feedback` is a real link with no "Soon" tag.
- **Constraints**: **404-never-403 both ways** (B's project id and B's feedback id read as A → 404; foreign `?project_id` → 404); **0** token/`vk_`/`vocky_session` leaks across 5 rendered pages; **no dark-mode toggle**.

### Three harness traps (my bugs, not the app's — do not "fix" the app for these)

Worth recording, because each one *looks* like a product defect:

1. **The BFF `403`s any POST without an `Origin` header.** `assertSameOrigin` requires it; a real browser always sends one on a fetch POST, so a scripted client must too. My first run read as "signup is broken" — it was not.
2. **`aria-current="page"` renders *before* `class`/`href`** on the rail's `<a>`. An attribute-order-dependent regex false-negatives. Match *within* the `<a>` tag, not by ordering. The rail was correct the whole time.
3. **`/feedback` uuids live only in RSC flight data (`<script>`) and `<option value>`**, never as visible cell text. Strip `<script>` before asserting "no bare uuid rendered". S5's actual claim was about *cell text*, and it holds.

## 3. Judgment against objective, intent, and docs

**The core question — is the authenticated web app (tenant dashboard + project detail) really built, hi2vi_web-style, as the replacement browser surface? Yes.** `intent.md`'s confirmed scope was exactly that, and the walk exercises it end-to-end.

**Accumulated deviations — all sound and honestly recorded** in `phase.md`:

- **S3 dropped `GET /app/tenant`** — sound. The shell already has the tenant from the `cache()`d `/auth/me`; a second call buys a round-trip and nothing else.
- **No `listCredentials`** — sound, and better than the alternative. The usage payload bundles the *identical* `serialize_credential` by design (the page exists to surface `last_used_at`), so the function would be dead code; `revalidatePath` refetches both together. The divergence from S3's "ignore the usage copy" rule is principled: there the usage copy was a *narrower* serializer.
- **S5's four** — the 5th file (`feedback-fields.tsx`, colocated, correctly *not* a domain-free `ui/` primitive); the 400/404→`notFound()` policy extended to the **list** (its own E2E requires a foreign `?project_id` → 404, which is a list fetch — the plan had specified detail-only, so extending it was necessary, not scope creep); the proxy's vocky 401→401 (a dead session means the same thing; 500 would blame us); and UTC-pinned timestamps (these render *server-side* — an unpinned zone silently prints the deploy box's clock as if it were local). All sound.

**The `soon` mechanism stays retained** — I confirm this is still the right call. It is ~10 lines with zero call sites, but its comment is now accurate ("No item sets it today — S5 shipped /feedback, the last one"), and P6 adds surfaces that will want exactly this affordance. Deleting it to re-add it in one phase is churn.

**Still-open items are correctly parked, not silently dropped:** admin-UI removal → **P6** (recorded in Open Questions and now resolved in the docs); brand palette → **P6** design gate; deploy → **P6**; **D2 stays deferred** (the dashboard is owner/session-scoped, so full-field exposure is appropriate — revisit only if a non-owner view is ever added).

**One non-blocking observation** (recorded for the P6 design gate, *not* a `changes_requested`): on `/projects/[id]` **no rail item is marked current** — it is not a rail item, and projects live on the dashboard. Defensible today with a 2-item rail; worth a deliberate call when the rail grows.

## 4. Doc consolidation — 8 versions

Docs only; no source touched (`git status -- src/ web/` is empty). Every version was authored **after reading `docs/current/<doc>.md`**, building on it — **P7's MCP content is preserved everywhere** (verified by count after each rebuild: architecture 15, decisions 18, api 15, security 8, product 4, experience 6, backend 10 MCP mentions intact). P4 landed *on top of* P7 despite the lower number.

| Doc | Version | What it says |
| --- | --- | --- |
| `frontend.md` | **v0002** | Authored fresh over the 363-byte stub — the phase's biggest doc job. The ported design system + the net-new `data-table`, `web/` structure, the BFF/session model, page/component inventory, the mutation rules the phase paid for, and the constraints. |
| `architecture.md` | v0006 | New "The Web App and the BFF Boundary" section; **resolved all four** dangling P4 refs (below). |
| `experience.md` | v0006 | New "The Web App" section, written **user-facing** (what you can do), not as a component inventory. |
| `decisions.md` | v0005 | **D-P4-1** (subdir `web/`), **D-P4-2** (BFF + sealed cookie), **D-P4-3** (port + defer the gate) — each with the real *why*. |
| `operations.md` | **v0002** | Authored fresh; **scoped to the web app**. |
| `product.md` | v0006 | **Authored, not skipped** — see below. |
| `security.md` | **v0005** | **The list's gap, authored** — see below. |
| `api.md` | v0006 | **Not on the list either** — see below. |

### The three judgment calls

**`security.md` v0005 — the plan flagged this gap; I agree it is warranted, and it earned its place twice over.**
The reasoning I'd defend: docs are organized **by concern, not by layer**. Someone auditing vocky's credential handling opens `security.md`, not `frontend.md` — and P4 introduced vocky's **first browser-held credential**, which is a genuinely new class of security truth, not a restatement of the frontend doc. It covers: the AES-256-GCM sealed httpOnly cookie (and *why* — an XSS cannot exfiltrate a 30-day bearer it cannot read); the BFF meaning the token never reaches browser JS (and therefore no CORS); the rate-limited/namespaced public auth pipeline preserving the backend's no-enumeration property at the browser edge; the show-once `vk_` key's single deliberate server→client crossing; the forced `Content-Disposition: attachment` (**`nosniff` does not save you when the declared type genuinely *is* `text/html`** — that is stored XSS against our own cookie); and backend-authz-preserved-at-the-web-surface. Confirming the call: `security.md` **also carried its own stale "Reshaping the operator surface is P4"** — the doc was already waiting on this phase.

**`product.md` v0006 — the plan called it a judgment call ("skip it if it adds nothing"). It was decided by fact, not taste.**
The Status line literally read *"Still upcoming in later phases: the tenant/project web app (P4)"* — **P4 made that false**. A doc asserting the phase's own deliverable is upcoming is not "nothing to add"; it is wrong. Beyond the correction, there is a real product-level fact per `intent.md` ("the packaged admin UI retires — this app replaces it"): the web app is now the primary user surface. Updated Status, First MVP, Goals, Product Direction, Accounts and Tenancy, and added the web app to **Product Surface Roles**.

**`api.md` v0006 — not on the Doc impact list, and I added it anyway.**
P4 changed **no API** — correctly, the list omits it. But P4's **completion falsified a statement inside it**: *"The packaged Admin Docs try-it flow still references it and is deferred to P4."* P4 is done and deliberately did **not** update those docs — it superseded the surface instead, deferring removal to P6. Left alone, that line tells a reader to expect a fix from a finished phase. I applied the same merits-not-list logic the plan itself applied to `security.md`, and made a one-line pointer correction (P4 → P6), honestly summarized as "no API contract change". The same stale line lived in `decisions.md`'s D-P2-4 consequences and was fixed in the v0005 already in flight.

### Resolving the admin-UI convergence question

The plan named `architecture.md:73`. **Grepping found four**, all resolved consistently — the replacement is **built** in P4; physical removal of `admin_ui.py` / `admin_assets/*` / the `/admin` mount is **P6**:

1. **Two-Track API** (`:73`) — "reshaping this operator surface is deferred to P4" → resolved **by replacement, not repair**.
2. **Configuration Surface** (`:143`) — "updating it is P4 work" → superseded; removed in P6.
3. **MVP Boundaries** (`:154`) — "reshaping is P4" → marked superseded; added the `web/` app as its own boundary entry.
4. **Open Questions** (`:355`) — the convergence question is **answered**; what remains is only removal *timing*. Replaced with two sharper questions: when the packaged UI is physically removed (and whether Admin REST outlives the UI it served), and whether the web app should ever carry feedback **management** (P4 deliberately kept it read+search only — a new decision if revisited).

## 5. Deviations from `plan.md`

- **Two doc versions beyond the plan's table** (`api.md` v0006, and `security.md` v0005 which the plan leaned toward but left to me) — reasoning above. Both are consolidations of durable truth P4 changed; neither touches source.
- **Resolved four P4 references in `architecture.md`**, not the one the plan named. The other three were the same question in different sections; fixing one would have left the doc self-contradictory.
- Otherwise none. No commits, no status transitions, no source edits.

## 6. State left behind

- **vocky is left healthy on `:8000`**, worker current. The Next dev server is **stopped**.
- `web/.env.local` remains in place (gitignored, untracked).
- Working tree: **docs + `works/` only**. `python3 scripts/workflow.py validate` passes.
- `review-phase` is the orchestrator's to run — this slice did not transition anything.
