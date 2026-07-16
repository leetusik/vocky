# P4.S4 — Plan: Project detail (info + credentials + project usage)

Orchestrator's native plan for slice **P4.S4** (`implementation`, `medium` → executed by **`slice-executor-mid`**). The per-project drill-down at `/projects/[projectId]`, plus the S3→S4 handoff that makes the dashboard's project rows link here.

## Context

S3 built the tenant dashboard and left two things for this slice: the reusable `components/usage/` pair (`StatTiles` + `TrendChart`, both documented "S4 reuses this as-is") and an explicit edit-site comment on the dashboard's project-name column awaiting the `/projects/[id]` link. S4 adds the credential lifecycle — the one place the app handles a **plaintext secret**.

## Verified contracts (exact)
- `GET /app/projects/{id}` → `200 {project}`; **400** non-UUID; **404** missing *or* cross-tenant (404-never-403 — ids can't be probed).
- `POST /app/projects/{id}/credentials` — optional `{name?}` (≤200, blank/whitespace → `null`; empty body also valid) → **201 `{credential, key}`**. `key` is the **plaintext `vk_…`, returned exactly once, never recoverable** (vocky persists only `sha256_hex(key)` + `key[:12]`).
- `DELETE /app/projects/{id}/credentials/{cid}` → **204**, empty body. `404` if not in this project.
- `GET /app/projects/{id}/usage` → `200 {window, totals, daily_counts, credentials}` — **no `project` object** (hence the separate header call), and **`credentials` uses the identical `serialize_credential`** as the standalone list endpoint.
- Credential: `{id, project_id, name|null, token_prefix, created_at, last_used_at|null, revoked_at|null}`. `token_prefix` = `key[:12]` (`"vk_"` + 9). **There is no `status` field — Active ⇔ `revoked_at === null`.** Revoked credentials remain listed. Oldest-first.
- **Ordering caveat:** `/app/projects/{id}/usage` resolves the project *before* the window, so a foreign id + bad date → 404 (not 400). We call it bare, so it's moot — but don't assume 400 precedence.
- **`daily_counts: []` cannot occur here** — `_project_usage_response` has no zero-project short-circuit; a capture-less project gets a **fully zero-filled** series. (`TrendChart` handles both regardless: `maxTotal` is floored at 1 and zero bars render as muted stubs.) Do **not** copy `VockyUsage`'s empty-series warning.

## Design calls (operator-approved)
- **Two parallel calls, and credentials come from the usage payload.** `Promise.all([getProject(token,id), getProjectUsage(token,id)])`; render the credentials table from `usage.credentials`. **This deliberately differs from S3's "ignore `usage.projects`" rule, for a principled reason:** there the usage copy was *narrower* (no `tenant_id`) and therefore lossy; here it is the **identical serializer**, and `_project_usage_response` bundles credentials *by design* for exactly this page (it exists to surface each key's `last_used_at`). **Do not add `listCredentials`** — it would be dead code (`revalidatePath` re-renders the page, which refetches usage+credentials).
- **`VockyMintedCredential`** — `createCredential` is the one endpoint that can't unwrap to a single domain type: unwrapping to `VockyCredential` would **throw away the only copy of the key**. Declare a public `VockyMintedCredential { credential: VockyCredential; key: string }` in `types.ts` (fits the file's style better than exporting a private `Raw*`).
- **Revoke via a hidden input**, not `action.bind` — keeps the `(prevState, formData)` action shape S3 established; validate `credentialId` as a UUID with zod.
- **Badges reuse the existing palette:** Active → `softGreen`, Revoked → `archive` (muted/inactive). **Do NOT add a `badgeVariants` variant** — the palette is a P6-swappable placeholder whose token *names* mirror hi2vi_web, so a new token name would have no source at the P6 swap. `Button` likewise has no `destructive` variant → revoke uses `secondary`.
- **Static page metadata** from `@/content` (not `generateMetadata` with the project name) — our client is `cache:"no-store"`, so a dynamic title would cost a second uncached fetch for a cosmetic gain.

## What S4 builds (all under `web/`)

**1. Client seam** — extend `web/src/lib/vocky/app.ts` in the established style (private `Raw*` envelope interfaces; reads `(token, ...pathArgs, signal?)`; **writes take no `signal`**; `encodeURIComponent` the ids):
```ts
getProject(token, projectId, signal?): Promise<VockyProject>            // reuse the EXISTING RawProjectResponse
createCredential(token, projectId, name?): Promise<VockyMintedCredential>  // body: name === undefined ? {} : {name}
revokeCredential(token, projectId, credentialId): Promise<void>         // sendJson<void>(…, "DELETE", undefined, {token}) — 204 → parseBody returns undefined
getProjectUsage(token, projectId, signal?): Promise<VockyProjectUsage>  // no envelope
```
Extend `web/src/lib/vocky/types.ts` under a new `// ── /app/projects/{id} shapes (P4.S4) ──` banner: `VockyCredential`, `VockyProjectUsage` (**separate type — no `projects`, has `credentials`**), `VockyMintedCredential`. Follow the file's rules: snake_case verbatim, ISO strings (never `Date`), each doc naming the Python serializer it mirrors, separate types over `Partial<>`.

**2. The page** — **new** `web/src/app/(app)/projects/[projectId]/page.tsx`, mirroring the dashboard's structure (metadata from content → module-level `columns` const + format helpers → `const { token } = await requireIdentity()` → `Promise.all` → `<div className="mx-auto max-w-page">` + `<h1 className="text-heading-3 text-ink">` + `<div className="mt-6 space-y-8">`). Next 16: **`params` is a Promise** → `const { projectId } = await params;`.
- **404 policy (new vs S3):** catch `ApiError` from the fetches — `status === 404 || status === 400` → `notFound()` (a malformed id is effectively not-found; never leak existence). `401` is already turned into a redirect by `requireIdentity`. **Everything else rethrows** — "an outage should surface, not masquerade as a missing project."
- Renders: `<h1>` project name; `StatTiles` + `TrendChart` (reuse **as-is**, passing this project's `totals`/`window`/`daily_counts`) — **exactly one usage block**, since both components hardcode DOM ids (`usage-totals` / `usage-trend`) and two would collide; the credentials `DataTable`; the mint form.
- Credentials table columns: Name (`name ?? content.unnamed`), Key (`token_prefix` + `…`, mono), Created, Last used (`last_used_at ?? content.never`), Status (`Badge` Active/Revoked from `revoked_at === null`), and a trailing `actions: true` column holding the revoke island. `rowKey={(c) => c.id}`; `empty` overridden from `@/content`. The island must be **imported** and rendered inside `cell` (the columns array is a module-level const in a server file).

**3. Mutations** — **new** `web/src/app/(app)/projects/[projectId]/actions.ts` (`"use server"` — **may export ONLY async functions**; the `*State` interface is fine since types are erased, but **no plain-value exports**, which silently register as extra server actions and 500 at runtime, per S3's live-caught bug):
- `mintCredentialAction(prevState, formData)` and `revokeCredentialAction(prevState, formData)`. Both follow S3's exact order: **zod-validate first** (cheap rejection, no round-trip) → **`requireIdentity()` OUTSIDE the `try`** (it signals "no session" via `redirect()`, which *throws*; a wrapping `catch` would swallow the bounce) → `try` wraps **only** the vocky call → `catch` maps `ApiError` **by status** (400/401/404 → copy; else generic) → `revalidatePath("/projects/[projectId]", "page")` — **the route pattern + `"page"` type arg**, not the concrete path.
- Mint's name is **optional** (vocky defaults it to `null`): zod `z.string().max(200).optional()`-shaped — **not** S3's `.min(1)`, and no `required` on the input.
- **The show-once key crosses the server→client boundary by design** — the single deliberate exception to S2/S3's "no vocky data crosses a client boundary" rule, because the user must see it exactly once. Mint's state carries `key?: string`; comment it explicitly. **Never log the key, never put it in a URL, never persist it.**

**4. Client islands** — **new** `mint-credential-form.tsx` (`"use client"`): `useActionState` + `INITIAL_STATE` **defined here, not in `actions.ts`**; on success renders a prominent, dismissible **"copy this now — it will never be shown again"** panel with the plaintext key (mono, selectable, plus a `navigator.clipboard` copy button) — the panel lives in the action state, so `revalidatePath`'s re-render keeps it until the next submit. **new** `revoke-credential-button.tsx` (`"use client"`): a per-row `<form action={…}>` with `<input type="hidden" name="credentialId">`, a **confirm step** before submitting, `pending` disabling, `Button variant="secondary"`.

**5. Copy** — **new** `web/src/content/project.ts`: `PROJECT` (`as const`, nested by section: title/lead, usage tiles, trend, credentials `{heading, columns:{}, empty, unnamed, never, statusActive, statusRevoked}`, mint form, key panel) + status-keyed `MINT_CREDENTIAL_ERRORS` / `REVOKE_CREDENTIAL_ERRORS`. Re-export from `web/src/content/index.ts` under a `// Project detail (P4.S4)` group (value + type on separate lines).

**6. The S3→S4 handoff** — modify `web/src/app/(app)/dashboard/page.tsx`: in the `name` column's `cell`, replace the `<span>` with `<Link href={`/projects/${project.id}`} className="font-medium text-ink hover:underline">`, add `import Link from "next/link"` (not currently imported; the page stays a server component), and **delete the now-stale "S4 owns that route" comment**.

**7. Tests** — extend `web/tests/vocky-app.test.ts` (same module under test). Add a `CREDENTIAL: VockyCredential` fixture; one `describe` per new fn asserting the **full request** (url + method + `Authorization: Bearer` + body) and the return. Cover: `getProject` unwraps; `createCredential` returns **both** `credential` and `key`; `revokeCredential` → `stubVocky(204, undefined)` → `resolves.toBeUndefined()` + `init.method === "DELETE"`; `getProjectUsage` passes through incl. an all-zero `daily_counts`; a 404 → `rejects.toMatchObject({name:"ApiError", status:404})`. **Note `lastCall()` reads `mock.calls[0]` (the FIRST call) despite its name** — index explicitly in any multi-fetch test. Keep it terse.

## Verification
1. `cd web && pnpm install` → `pnpm typecheck` → `pnpm lint` → `pnpm test` → `pnpm build` — all green. **Confirm the build registers exactly the expected server actions** (S3's bug class).
2. **Live E2E — vocky is running on `:8000`** (confirm `/healthz` → 200). Start web with `VOCKY_API_BASE_URL=http://127.0.0.1:8000` + a `SESSION_SECRET`; curl cookie jar is fine. Drive:
   - signup → create a project → **follow the dashboard's new project link** to `/projects/{id}` (proves the handoff) → page renders name + all-zero usage (zero-filled bars, not an empty state) + the empty credentials state.
   - **Mint (unnamed)** → the plaintext `vk_…` key is shown **once** and matches `vk_[A-Za-z0-9_-]+` → **reload** → the key is **gone** (only `token_prefix` remains). Mint a **named** one → name renders.
   - **Revoke** → confirm → status flips **Active → Revoked**, the row **remains listed**, and the key stays revoked after reload.
   - **404 paths:** a random UUID → 404 page; a malformed id (`not-a-uuid`) → 404 page; and **a second user's project id → 404** (sign up user B, create project B, request it as user A — proves no cross-tenant existence leak).
   - **Secret hygiene:** the plaintext key appears in the mint response render only — `grep` the web server logs to confirm it was never logged.
3. `python3 scripts/workflow.py validate`.
- **Fallback:** if the live run is blocked, complete (1), capture the exact failing command + error, and return **`needs_operator`**. Never claim a live pass you didn't drive.

## Executor guardrails
- **Do NOT touch:** `client.ts`, `auth-guards.ts`, `session.ts`, `env.ts`, `bff.ts`, `app-shell/*`, `data-table.tsx`, `components/usage/*` (reuse as-is), `badge.tsx`/`button.tsx` (no new variants), `vitest.config.ts`, `.env.example`. No new env, no new deps.
- Everything lands under `web/`; **no** `src/vocky/**` edits; **no** `works/**` except `works/phases/active/P4/slices/P4.S4/result.md` + one `phase.md` "Landed changes" line.
- **No** commits, **no** `doc-new-version`, **no** status transitions. Return a structured verdict.
