# P10.S4 — Web app: org-keys panel, nullable credential type, Workspace → Org

kind `implementation` · risk **medium** → `slice-executor-mid` · depends `P10.S3`

All paths below are relative to `/Users/sugang/projects/personal/vocky`. **This slice touches `web/`
only** — no Python, no docs.

## Context

The backend is done. S1 added the schema, S2 made every credential-derived project filter org-aware, and
S3 turned org keys on. What S4 must build against (all verified, from `phase.md § P10.S3 landed`):

| route | request | response |
|---|---|---|
| `POST /app/credentials` | optional `{"name"?: string\|null}`, empty body allowed, `max_length=200` | `201 {credential, key}` — plaintext key returned **once** |
| `GET /app/credentials` | — | `200 {credentials: [...]}` — org-level rows **only**, oldest-first, **including revoked** |
| `DELETE /app/credentials/{credential_id}` | — | `204`; `400` malformed UUID; `404` otherwise |

**The single most important client fact:** the credential payload is unchanged —
`{id, project_id, name, token_prefix, created_at, last_used_at, revoked_at}` — and for an org row
**`project_id` is JSON `null`**. There is no new field and no scope discriminator:
**`project_id === null` *is* the "org key" signal.** That is what a client branches on.

The two listings are disjoint in both directions (`GET /app/credentials` is org-only;
`/app/projects/{id}/credentials` is project-only), so a tenant's keys enumerate exactly once across the
two surfaces. **An org key deliberately does not appear in any project's drill-down** — which is exactly
why the dashboard needs its own panel.

Decided at DECOMP (operator decision 1): **no design round.** The org-keys surface is a panel on
`/dashboard` — no new route, no new rail entry — built from shipped primitives.

## Scope

### 1. Type widening (`web/src/lib/vocky/types.ts`)

`VockyCredential.project_id: string` → `string | null`, with a doc comment saying `null` means an
org-level key spanning every project in the org, and that consumers needing a project id for a
project-bound credential should read it from the project in scope, not from here.

**This breaks exactly one site:** `web/src/app/(app)/projects/[projectId]/page.tsx:109`
(`projectId={credential.project_id}` into `RevokeCredentialButton`'s `projectId: string`). Narrow it with
an **explicit guard**, not a cast — a project-detail credential is always project-bound, so the guard is
a type narrow, not new behavior. Say that in a comment.

`VockyFeedback.project_id` is a **different** type and already nullable — do not touch it.

### 2. BFF client (`web/src/lib/vocky/app.ts`)

Add `listOrgCredentials` / `createOrgCredential` / `revokeOrgCredential` following the file's existing
conventions exactly:

- `token: string` is a **required first positional arg**; reads take a trailing optional
  `signal?: AbortSignal`, writes do not.
- **Return the mint envelope whole** as `VockyMintedCredential` — unwrapping it would discard the only
  copy of the plaintext key. (Every other function unwraps; this one is the deliberate exception, and
  `createCredential` already shows the pattern.)
- Optional name body: `name === undefined ? {} : { name }` — send `{}`, never `{name: null}`.
- `encodeURIComponent` the credential id in the DELETE path.
- **Add no caching flags** — `cache: "no-store"` is baked into `getJson`/`sendJson`.
- Don't catch `ApiError`; enumerate the meaningful statuses in the JSDoc, as `getProject` does.
- Defensive `?? []` when unwrapping the list envelope.

### 3. The dashboard panel (`web/src/app/(app)/dashboard/`)

**Slot:** a fourth `<section aria-labelledby="org-keys">` inside `page.tsx`'s `mt-6 space-y-6` stack,
after the projects section. The stack is already full-width — no layout work. **Do not collide with the
existing `usage-totals` / `usage-trend` DOM ids.**

Mirror the projects/credentials section shape: `<h2 id>` → lead `<p>` → `<DataTable className="mt-4">` →
`<Card variant="base" className="mt-4">` wrapping the mint form.

**Data:** the page fetches `listProjects` + `getUsage` in one `Promise.all`; **neither carries org
credentials**, so add `listOrgCredentials(token)` as a third leg of that same `Promise.all`. Let anything
non-401 propagate to the error boundary — do not swallow a failure into an empty panel.

**Columns:** define a **slimmer column set local to the dashboard** — name / key (`token_prefix`) /
created / last used / status / actions. Do **not** extract a shared parameterized `credentialColumns`
factory: the org table has no project binding, its actions cell differs, and extraction would edit the
shipped project page for marginal gain. No project column — the list is org-only by construction.
Reuse `Badge variant="active"|"revoked"` (derived from `revoked_at === null`) and
`Button variant="destructiveOutline" size="sm"`, and override `DataTable`'s built-in `empty` default so
the empty copy comes from `@/content` like every other call site.

**The show-once key panel — lift it, don't copy it.** `ShowOnceKey` is currently module-private inside
`web/src/app/(app)/projects/[projectId]/mint-credential-form.tsx`. Move it to a shared component under
`web/src/components/` taking its copy as a prop, and have both mint forms use it.

**Preserve its dismissal logic verbatim:**

```
const [dismissedAt, setDismissedAt] = useState<number | null>(null);
const showKey = state.key !== undefined && state.ok !== undefined && state.ok !== dismissedAt;
```

Dismissal is keyed by the `ok` success stamp, **not a boolean**. A boolean would swallow the *next*
minted key — and since the plaintext is shown exactly once and only a hash is stored, that loss is
unrecoverable. This is the one piece of this slice where a "simplification" is a real bug.

**Islands:** the table stays **server-rendered**; only the mint form and the per-row revoke button are
`"use client"`. A revoke button rendered inside a server column cell is already how the project page
works and is fine. For the org form, prefer a sibling `MintOrgCredentialForm` / org revoke island over
making `projectId` optional on the existing ones — the existing components stay untouched.

### 4. Server actions (`web/src/app/(app)/dashboard/actions.ts`)

- **`"use server"` files may export only async functions — and a violation fails at REQUEST time.**
  `pnpm typecheck`, `pnpm lint` and `pnpm build` all pass it. So the new form's `INITIAL_STATE` **must**
  live in the client island. Green CI does not prove this correct.
- State shape `{ error: string | null; ok?: number }` plus `key?: string` for mint, where `ok` is a
  `Date.now()` stamp bumped on each success. Action signature
  `(_prevState, formData) => Promise<State>`; ids ride as **hidden inputs**, not `action.bind`.
- `await requireIdentity()` goes **outside** the `try` — it signals "no session" by `redirect()`, which
  throws, and catching it would swallow the bounce to `/login`.
- zod `safeParse` only. Credential name: `z.string().max(200).optional()`, blank/whitespace normalized to
  `undefined` so the body omits the field. Credential id: `z.uuid()`.
- Map errors **by HTTP status only, never by vocky's `detail` text**, against a new status-keyed
  `ORG_CREDENTIAL_ERRORS` beside `CREATE_PROJECT_ERRORS`; uncovered statuses fall through to `generic`.
- **`revalidatePath("/dashboard")` with no second argument** — `/dashboard` is static. Do **not** copy
  the `("/projects/[projectId]", "page")` form from the project action; the route-pattern-plus-type
  variant is for dynamic routes and passing the wrong shape silently revalidates nothing.

### 5. Copy (`web/src/content/`)

New org-keys copy goes in `dashboard.ts` and must be added to the `content/index.ts` barrel with the
usual `// P10.S4 — …` comment. Never inline a string in a component.

**Workspace → Org, the complete list:**

- `web/src/content/app.ts:33` — `workspaceLabel: "Workspace"`. **Rename the key to `orgLabel` as well as
  the value**; a key named `workspaceLabel` holding `"Org"` misleads the next reader. One consumer,
  `web/src/components/app-shell/app-shell.tsx:38` (and a stale comment at `:11`).
- `web/src/content/auth.ts:47` — login sub, "Access your workspace, projects, and feedback."
- `web/src/content/auth.ts:62` — signup sub, "A workspace is created for you automatically." This one is
  also now **understated**: signup provisions an org **and** a `"default"` project.

The phase constraint "label values only" governs **wire identifiers** — `tenant_id`, `tenants[]`,
`VockyTenant`, and every route keep their names. An internal content key is not a wire identifier.

**Stale claims to fix — four sites, same false statement.** `UNIQUE(tenant_id, name)` now exists:
`web/src/lib/vocky/types.ts:56-58`, `web/src/lib/vocky/app.ts:62-63` (whose `createProject` JSDoc also
needs the get-or-create/idempotency note), `web/src/app/(app)/dashboard/page.tsx:116-117`, and
`web/tests/vocky-app.test.ts:101-109` plus its header comment at `:24`.

**Note carefully:** that test still *passes* — it asserts the client passes duplicates through, not that
the backend permits them. Only its **name and rationale** are wrong. Keying rows on `id` rather than
`name` stays correct regardless; fix the reasoning, keep the behavior.

**Near-unreachable empty states** (`phase.md` open question, S4's call): `dashboard.ts:69`
(`projects.empty`), `feedback.ts:56` (`emptyNoProjects`), and `dashboard.ts:53-54` (`trend.empty` and its
zero-project rationale) are now effectively unreachable because signup provisions `"default"`.
**Recommendation: keep them as defensive fallbacks, fix the now-false rationale comments.** They cost
nothing and an empty list is still representable. Record the call either way.

**Out of scope: all landing copy** (`web/src/content/landing.ts`, including "Per-project API keys" at
`:181-184`) — that is P11's, per operator decision 4. Note it; do not change it.

### 6. Tests (`web/tests/vocky-app.test.ts`)

Three `describe` blocks beside the existing `createCredential` / `revokeCredential` ones, following the
file's conventions: `stubVocky` uses **`mockImplementation`, not `mockResolvedValue`** (a `Response` body
can only be consumed once), and assertions check the absolute URL, `init.method`, the exact
`JSON.stringify` body, and the `Authorization` header.

Cover: the list unwraps and tolerates a missing envelope; the mint returns `{credential, key}` **whole**
and sends `{}` when no name is given; the revoke issues a DELETE to the encoded path. Add a
null-`project_id` org sibling to the existing `CREDENTIAL` fixture.

## Verification

Run from `web/` (pnpm 10.28.2, Node ≥ 22.13):

```bash
pnpm install
pnpm typecheck     # tsc --noEmit — must be clean, incl. the one narrowed site
pnpm lint
pnpm test          # vitest run
pnpm build         # next build
pnpm format:check
```

**`pnpm build` is not optional here** — it is the only one of these that exercises the real `server-only`
package (vitest aliases it to an inert stub). None of them catch a `"use server"` non-async export, so
**re-read `actions.ts` and confirm by eye that every export is an async function.**

## Definition of done

`VockyCredential.project_id` is `string | null` with the single consumer explicitly narrowed; the
dashboard has a working org-keys panel that lists, mints (show-once), and revokes; the show-once
dismissal remains stamp-keyed; Workspace → Org copy is complete; the four stale non-uniqueness claims are
corrected; all six web commands pass; `result.md` and the `phase.md` notes are written.

**No `doc-new-version`** — append one-line **Doc impact** notes to `phase.md`; `P10.REVIEW` consolidates.
