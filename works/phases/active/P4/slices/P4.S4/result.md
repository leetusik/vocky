# P4.S4 — Result: Project detail (info + credentials + project usage)

Shipped `/projects/[projectId]` — the per-project drill-down — plus the S3→S4
handoff that makes the dashboard's project names link into it. This is the app's
only handler of a plaintext secret. Everything landed under `web/`; no
`src/vocky/**` edits, no new env, no new deps, none of the guardrail files
touched.

Both verification tiers ran: the in-sandbox gate is green **and** the live E2E
drove every required path against the running vocky — **40/40 checks**, including
the cross-tenant 404 and the show-once key's disappearance on reload.

## What was built (all under `web/`)

**Client seam** — `src/lib/vocky/app.ts` extended in the established style
(private `Raw*` envelopes, `(token, …pathArgs, signal?)` reads, `signal`-less
writes, `encodeURIComponent`d ids): `getProject` (reuses the existing
`RawProjectResponse`), `createCredential`, `revokeCredential`
(`sendJson<void>` — the `auth.ts::logout` idiom; `parseBody` maps 204 →
`undefined`), `getProjectUsage` (bare, no envelope). `types.ts` extended under
the S4 banner with `VockyCredential`, `VockyProjectUsage` (separate type — no
`projects`, has `credentials`), `VockyMintedCredential`. `client.ts` untouched.

**Page** — `(app)/projects/[projectId]/page.tsx`: `const { projectId } = await
params` (Next 16) → `requireIdentity()` → `Promise.all([getProject,
getProjectUsage])`. Credentials render from `usage.credentials` — the deliberate
divergence from S3's "ignore `usage.projects`" rule, and a principled one: there
the usage copy was a *narrower* serializer, here it is the *identical*
`serialize_credential`, bundled by `_project_usage_response` by design for this
page. No `listCredentials` was added — it would be dead code.

**404 policy** — the fetches are wrapped in a `loadProject()` helper so
`notFound()` can never sit inside the `try` (it signals by throwing, like
`redirect()`). `ApiError` 404 **or** 400 → `notFound()`; a malformed id is
effectively not-found, and distinguishing them would leak the shape of what
exists. Everything else rethrows — an outage should surface, not masquerade as a
missing project.

**Usage** — `StatTiles` + `TrendChart` reused **as-is**, exactly one block (both
hardcode `usage-totals` / `usage-trend` DOM ids). Per the plan, no empty-series
warning was copied from `VockyUsage`: this route has no zero-project
short-circuit. `TrendChart`'s required `empty` prop still gets a defensive string,
documented as unreachable here. **Confirmed live: 31 zero-filled bars on a
capture-less project**, never the empty state.

**Mutations** — `actions.ts` (`"use server"`, only async functions + a type):
`mintCredentialAction` / `revokeCredentialAction`, both in S3's order —
zod-validate → `requireIdentity()` **outside** the `try` → `try` wraps only the
vocky call → `catch` maps by **status** (400/401/404 → copy, else generic) →
`revalidatePath("/projects/[projectId]", "page")` (route pattern + `"page"`).
Mint's name is optional (`z.string().max(200).optional()`, no `required` on the
input); blank/whitespace normalizes to `undefined` so the body is `{}` and vocky
stores `null`.

**Islands** — `mint-credential-form.tsx` + `revoke-credential-button.tsx`, both
with `INITIAL_STATE` defined in the island (never in the `"use server"` file).
Revoke uses hidden `projectId` + `credentialId` inputs (keeping the
`(prevState, formData)` shape) and an inline two-step confirm; `Button
variant="secondary"` — no new `badgeVariants`/`buttonVariants` token was added,
so the P6 gate swaps values only. Badges: Active → `softGreen`, Revoked →
`archive`, derived from `revoked_at === null` (vocky has no `status` field).

**Copy** — new `src/content/project.ts` (`PROJECT` + `MINT_CREDENTIAL_ERRORS` +
`REVOKE_CREDENTIAL_ERRORS`), re-exported from `content/index.ts`.

**Handoff** — `(app)/dashboard/page.tsx`: the name column's `<span>` is now a
`<Link href={`/projects/${project.id}`}>`, `import Link from "next/link"` added,
and the stale "S4 owns that route" comment deleted. The page stays a server
component.

## The show-once key

vocky returns the plaintext `vk_` key exactly once and persists only
`sha256_hex(key)` + `key[:12]`, so `createCredential` returns the **whole
envelope** (`VockyMintedCredential`) — unwrapping to `VockyCredential` would
discard the only copy in existence. The key then crosses the server→client
boundary in the **action state** — the single deliberate exception to S2/S3's "no
vocky data crosses a client boundary" rule, commented as such in both
`MintCredentialState.key` and the island.

Living in the action state (not the server-rendered tree) is what makes the panel
**survive `revalidatePath`'s re-render** and **vanish on the next submit or
navigation**. It is never logged, never in a URL, never persisted. Dismissal is
keyed by the state's `ok` stamp rather than a boolean — a sticky `dismissed` flag
would silently swallow the *next* minted key, the one case where a missed render
is unrecoverable. **Verified live: the key appears once, and is gone after a
reload with only the 12-char `token_prefix` stub remaining; `grep` finds no `vk_`
string of any length in the web logs.**

## Verification

### A. In-sandbox gate — all green

| Command | Outcome |
| --- | --- |
| `pnpm install --frozen-lockfile` | **pass** — no new deps |
| `pnpm typecheck` | **pass** |
| `pnpm lint` | **pass** |
| `pnpm test` | **pass** — **50/50** (44 S2/S3 + 6 new) |
| `pnpm build` | **pass** — `/projects/[projectId]` is `ƒ (Dynamic)` |
| server-action manifest (S3's bug class) | **pass** — **exactly 3**: 1 × dashboard, 2 × project page (mint + revoke). No stray registration. |
| `python3 scripts/workflow.py validate` | **pass** |

### B. Live E2E — **RAN** against vocky on `:8000` (`/healthz` → 200) — **40/40**

Driven JS-less: each server-action submit replays the rendered `$ACTION_*` hidden
inputs as a multipart POST, so the real progressive-enhancement path ran.

| # | Check | Result |
| --- | --- | --- |
| 1 | signup A → sealed cookie → dashboard | **200** |
| 2 | create project → **follow the dashboard's NEW link** | **1** `/projects/{uuid}` link; page **200** (handoff proven) |
| 3 | Capture-less project usage | **31 zero-filled bars**, not the empty state |
| 4 | Credentials empty state; no `vk_` on a fresh page | **rendered** / **none** |
| 5 | **Mint unnamed** → key shown **once** | `vk_…` (46 chars), matches `vk_[A-Za-z0-9_-]+`; "only time this key will ever be shown" panel; row reads "Unnamed key" |
| 6 | **RELOAD → key GONE** | **no `vk_` key in the HTML**; only `token_prefix` (`vk_8ywxxiSZ1`) remains; Active / "Never" |
| 7 | **Mint named** ("Production") | name renders; its own distinct key shown once |
| 8 | **Revoke** → confirm → submit | **Active → Revoked**, **row remains listed**, persists across reload, other key still Active, no key leaked |
| 9 | Random UUID → **404** | **404** |
| 10 | Malformed id (`not-a-uuid`) → **404** | **404** (vocky's 400 mapped — never leaks the shape) |
| 11 | **Cross-tenant: user B's project id, as user A** | **404** — and B reads the same id **200**. The access log shows both: `GET /projects/0471b058… 200` (B) then `404` (A). Name never leaked. |
| 12 | **Secret hygiene** — `grep` the web logs | **0** occurrences of the key; **0** `vk_` strings of any length; 0 errors/500s/warnings |

**One environment note (no code impact):** the live run uses `pnpm dev`, not
`pnpm start`. `session.ts` sets the session cookie `Secure` when
`NODE_ENV === "production"`, so a plain-http client on 127.0.0.1 never replays it
and every guarded page bounces to `/login`. Dev is plain http, exactly as
`session.ts`'s own comment anticipates. (Real browsers treat `127.0.0.1` as a
secure context and would accept it; Python's cookiejar does not implement that
exception.) The production build was still exercised in full by the `pnpm build`
gate above. **S5 should drive its live E2E on `pnpm dev` for the same reason.**

**Not driven live (out of scope, no code impact):** a **non-zero** usage series
and a non-null `last_used_at` — the local docker `worker` is a stale image
(S3's gotcha), so captures never surface. Both paths are covered by unit test +
construction; the zero-filled path is the one that renders here anyway.

**vocky left running and healthy on `:8000` for S5**; the web dev server was
stopped.

## Deviations from plan.md

- **`content/project.ts` exports no type of its own**, so `content/index.ts` got
  the value-export line but no type line (the plan sketched "value + type on
  separate lines"). Its one type need, `StatTileCopy`, already lives in
  `dashboard.ts` and is re-exported there — duplicating it would fork the
  contract `StatTiles` reads.
- **The revoke confirm is client-state**, so before hydration the Revoke button is
  a no-op rather than a working JS-less form (the mint form has no such gate and
  works JS-less; the live E2E drives revoke through the same no-JS action path).
  This follows the plan's explicit "confirm step before submitting", and for an
  irreversible action a pre-hydration no-op beats an accidental one-click revoke.
- Otherwise none. `web/` only; no `works/**` beyond this file + one `phase.md`
  line; no commits, no `doc-new-version`, no status transitions.
