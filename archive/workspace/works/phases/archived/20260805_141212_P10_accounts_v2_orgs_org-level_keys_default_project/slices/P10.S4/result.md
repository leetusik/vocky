# P10.S4 result — Web app: org-keys panel, nullable credential type, Workspace → Org

## What landed

1. **Type widening** — `VockyCredential.project_id: string` → `string | null` in
   `web/src/lib/vocky/types.ts`, with a doc comment explaining `null` ⇔ org-level. The one hard TS
   error the plan predicted (`projects/[projectId]/page.tsx`'s `RevokeCredentialButton` cell) was
   fixed with an explicit two-step narrowing guard (`revoked_at !== null`, then `project_id ===
   null` → `null`), not a cast, with a comment stating the invariant it relies on (this page's
   credentials always come from a per-project `usage` payload, which never contains org keys).
   `VockyFeedback.project_id` (a different, already-nullable type) was untouched.

2. **BFF client** — `listOrgCredentials` / `createOrgCredential` / `revokeOrgCredential` added to
   `web/src/lib/vocky/app.ts`, following the file's existing conventions: `token` required first
   positional arg, reads take an optional trailing `signal`, writes don't; `createOrgCredential`
   returns the mint envelope WHOLE (never unwrapped — same deliberate exception as
   `createCredential`); optional name sends `{}`, never `{name: null}`; credential id
   `encodeURIComponent`'d; no extra caching flags (`getJson`/`sendJson` already bake in
   `cache: "no-store"`); errors enumerated by status in JSDoc, not caught.

3. **Dashboard panel** — a fourth `<section aria-labelledby="org-keys">` in
   `web/src/app/(app)/dashboard/page.tsx`'s `mt-6 space-y-6` stack, after the projects section.
   `listOrgCredentials(token)` joins the page's existing `Promise.all` as a third leg (alongside
   `listProjects` / `getUsage`) — no sequential round-trip. A dashboard-local, slimmer
   `orgCredentialColumns` (name/key/created/lastUsed/status/actions, no project column) mirrors the
   project page's `credentialColumns` shape without extracting a shared factory, per the plan — the
   org table's actions cell renders a different, non-project-scoped revoke island.

4. **Show-once key panel lifted, not copied** — new shared component
   `web/src/components/show-once-key.tsx` (`ShowOnceKey`, `"use client"`, takes a
   `copy: ShowOnceKeyCopy` prop). `projects/[projectId]/mint-credential-form.tsx` now imports it
   instead of defining it module-privately; the new `dashboard/mint-org-credential-form.tsx` uses
   it too. **Dismissal logic preserved verbatim** in both call sites:
   ```ts
   const [dismissedAt, setDismissedAt] = useState<number | null>(null);
   const showKey = state.key !== undefined && state.ok !== undefined && state.ok !== dismissedAt;
   ```
   Stamp-keyed, not boolean-keyed — untouched, as the plan required.

5. **Server actions** — `mintOrgCredentialAction` / `revokeOrgCredentialAction` appended to
   `web/src/app/(app)/dashboard/actions.ts`. Signature `(_prevState, formData) => Promise<State>`;
   ids ride as hidden inputs; `requireIdentity()` sits OUTSIDE every `try` (it signals "no session"
   via `redirect()`, which throws); zod `safeParse` only (`z.uuid()` for the credential id,
   `z.string().max(200).optional()` for the name, blank/whitespace normalized to `undefined` so the
   body omits the field); errors mapped by HTTP status only against a new status-keyed
   `ORG_CREDENTIAL_ERRORS` in `content/dashboard.ts` (one object covering both mint and revoke,
   since both actions live on a single panel — unlike `project.ts`'s split
   `MINT_CREDENTIAL_ERRORS`/`REVOKE_CREDENTIAL_ERRORS`). **`revalidatePath("/dashboard")` takes no
   second argument** in both new actions (verified by eye — `/dashboard` is static, unlike
   `/projects/[projectId]`). **Every export in `dashboard/actions.ts` is either an async function
   (`createProjectAction`, `mintOrgCredentialAction`, `revokeOrgCredentialAction`) or a type-only
   interface (`CreateProjectState`, `MintOrgCredentialState`, `RevokeOrgCredentialState`)** — checked
   by re-reading the whole file after editing, per the plan's warning that green CI does not catch a
   `"use server"` non-async export. The two new forms' `INITIAL_STATE` constants live in their
   client islands (`mint-org-credential-form.tsx` / `revoke-org-credential-button.tsx`), never in
   `actions.ts`.

6. **Copy — new org-keys section + Workspace → Org, complete**:
   - `content/dashboard.ts` gained `DASHBOARD.orgKeys` (heading/lead/columns/mint/keyPanel/revoke)
     and `ORG_CREDENTIAL_ERRORS`, both re-exported from `content/index.ts`.
   - `content/app.ts`: `workspaceLabel: "Workspace"` → `orgLabel: "Org"` — key AND value renamed
     (a `workspaceLabel` key holding `"Org"` would mislead the next reader). Updated the one
     consumer, `components/app-shell/app-shell.tsx:38`, and its stale "workspace/user" doc comment
     (now "org/user").
   - `content/auth.ts`: login sub → "Access your org, projects, and feedback."; signup sub → "An org
     and a default project are created for you automatically." (previously understated — it now
     names both provisioned resources).
   - Landing copy (`content/landing.ts`) deliberately untouched — P11's, per the phase's decision 4.

7. **Four stale non-uniqueness claims corrected** (falsified by `P10.S1`'s
   `UNIQUE(tenant_id, name)`):
   - `web/src/lib/vocky/types.ts` — `VockyProject`'s doc comment.
   - `web/src/lib/vocky/app.ts` — `createProject`'s JSDoc, now noting get-or-create/idempotency.
   - `web/src/app/(app)/dashboard/page.tsx` — the `rowKey` comment near the projects `DataTable`.
   - `web/tests/vocky-app.test.ts` — the "keeps duplicate-named projects distinct" test, renamed
     to "passes distinct projects through keyed on id, not name" and rewritten to stop asserting a
     same-name scenario vocky can no longer produce, while keeping the still-true assertion (client
     keys on `id`). The test passed both before and after this rewrite — only its name/rationale
     were wrong, never its behavior, per the plan's note.

8. **Near-unreachable empty states — kept, per the plan's recommendation.** All three sites
   (`DASHBOARD.projects.empty`, `DASHBOARD.trend.empty`, `FEEDBACK.list.emptyNoProjects`) keep
   their copy unchanged; only their doc comments were updated to note they are now
   near-unreachable via signup (which provisions a `"default"` project) rather than implying "zero
   projects" is a live onboarding state. They cost nothing and stay representable as defensive
   fallbacks. `project.ts:82` (`PROJECT.trend.empty`) was already correctly documented pre-P10 as
   defensive-only for a different reason (a capture-less *project* still zero-fills; only a
   *tenant* with zero projects short-circuits) and was out of this slice's plan scope — left as is.

9. **Tests** — three new `describe` blocks in `web/tests/vocky-app.test.ts`:
   `listOrgCredentials` (unwraps, tolerates a missing envelope key), `createOrgCredential` (returns
   `{credential, key}` whole, sends `{}` with no name / `{name}` with one), `revokeOrgCredential`
   (DELETEs the encoded path, resolves `undefined` on 204). All follow the file's
   `mockImplementation`-per-call convention (a `Response` body can only be consumed once) and assert
   the absolute URL, `init.method`, exact `JSON.stringify` body, and `Authorization` header. Added a
   null-`project_id` `ORG_CREDENTIAL` fixture as a sibling of the existing `CREDENTIAL`. Test count:
   61 (up from 55).

## Verification (run from `web/`)

```
$ pnpm install
Lockfile is up to date, resolution step is skipped — Already up to date

$ pnpm typecheck    # tsc --noEmit
PASS — no output, clean

$ pnpm lint          # eslint .
PASS — no output, clean

$ pnpm test          # vitest run
PASS — Test Files 5 passed (5), Tests 61 passed (61)

$ pnpm build         # next build
PASS — "Compiled successfully", all 17 routes generated, TypeScript pass inside build clean too.
This is the one command that exercises the real `server-only` package (vitest aliases it to an
inert stub), and it succeeded — confirming the `"use server"` files load correctly at build/runtime.

$ pnpm format:check  # prettier --check .
FAILS at the repo level (exit 1), but every file this slice edited is clean. See "Deviations".
```

**By-eye confirmation (the plan's #1 footgun, not provable by green commands):** re-read
`web/src/app/(app)/dashboard/actions.ts` in full after editing. Every export is either an `async
function` (`createProjectAction`, `mintOrgCredentialAction`, `revokeOrgCredentialAction`) or a
type-only `interface` (`CreateProjectState`, `MintOrgCredentialState`, `RevokeOrgCredentialState`,
erased before the `"use server"` loader sees the module). No plain-value export exists.

## Deviations from `plan.md`

1. **`pnpm format:check` exits 1 at the repo level, but not because of this slice.** Ran it before
   any edits (`git stash`) and confirmed 15 pre-existing unformatted files at baseline — none of
   this slice's business, in files this slice never touches (`README.md`,
   `projects/[projectId]/actions.ts`, `apple-icon.tsx`, `opengraph-image.tsx`, `lib/bff.ts`,
   `lib/env.ts`, `lib/session.ts`, `lib/vocky/auth.ts`, four test files). Six of the files this
   slice *did* edit had drifted from Prettier (3 were already in that pre-existing-15 list before my
   edits, 3 newly created/edited files also drifted) — ran `prettier --write` on exactly the files
   this slice touched, re-ran the full suite, and confirmed `pnpm format:check` now reports clean
   for every file this slice changed; the remaining 12 warnings are 100% pre-existing, unrelated
   files (verified by `git stash` diff of the warning list before vs. after this slice's edits).
   Not a scope change — this slice's own contribution is formatter-clean; the repo-wide command
   still exits 1 because of debt this slice didn't create and wasn't asked to fix.

2. **Empty-state call**: kept all three near-unreachable empty states as defensive fallbacks (the
   plan's explicit recommendation), fixing only their now-false rationale comments. Recorded per the
   plan's instruction to "record the call either way."

No other deviations. Every route shape, error-mapping rule, and copy-token instruction in
`plan.md` was followed as written.

## Doc impact

Appended to `phase.md`'s "Doc impact" running list (no `doc-new-version` run — review consolidates):

- **`experience.md`** — the signup copy is now literally "An org and a default project are created
  for you automatically" in the web app, matching the wording direction `P10.S1`'s doc-impact note
  already called for.
- **`product.md` / `experience.md`** — the org-vs-project key choice (already documented by
  `P10.S3`'s doc-impact note) is now visibly live in the product; no new concept, just confirmation
  it shipped in the web UI.

No new durable-truth facts beyond what `P10.S1`–`P10.S3` already flagged — this slice is the web-side
implementation/confirmation of those, not a new backend or contract change.

## Cross-slice notes for S5 (CLI)

Full detail is in `phase.md`'s "P10.S4 landed" section. Summary: S5 inherits the exact route shapes
`P10.S3` documented (`POST`/`GET`/`DELETE /app/credentials`, `project_id === null` as the sole
org-key signal, 404-never-403-and-narrower-than-per-project-delete), plus the completed Workspace →
Org wording pattern from the web app (`orgLabel`, "org" not "workspace" throughout, same frozen wire
identifiers `tenant_id`/`tenants[]`/`VockyTenant`/every route name).

## Files changed

- `web/src/lib/vocky/types.ts` — `VockyCredential.project_id` widened; `VockyProject` doc fixed.
- `web/src/lib/vocky/app.ts` — `listOrgCredentials`/`createOrgCredential`/`revokeOrgCredential`
  added; `createProject` JSDoc fixed.
- `web/src/components/show-once-key.tsx` — new shared component.
- `web/src/app/(app)/projects/[projectId]/mint-credential-form.tsx` — uses the shared component.
- `web/src/app/(app)/projects/[projectId]/page.tsx` — explicit `project_id` narrow guard.
- `web/src/app/(app)/dashboard/page.tsx` — org-keys panel, `orgCredentialColumns`, `rowKey` comment
  fix, `Promise.all` third leg.
- `web/src/app/(app)/dashboard/actions.ts` — `mintOrgCredentialAction`/`revokeOrgCredentialAction`.
- `web/src/app/(app)/dashboard/mint-org-credential-form.tsx` — new client island.
- `web/src/app/(app)/dashboard/revoke-org-credential-button.tsx` — new client island.
- `web/src/components/app-shell/app-shell.tsx` — `orgLabel` consumer + comment fix.
- `web/src/content/app.ts` — `workspaceLabel` → `orgLabel`.
- `web/src/content/auth.ts` — login/signup sub copy.
- `web/src/content/dashboard.ts` — `ORG_CREDENTIAL_ERRORS`, `DASHBOARD.orgKeys`, empty-state
  comments fixed.
- `web/src/content/feedback.ts` — `emptyNoProjects` comment fixed.
- `web/src/content/index.ts` — barrel export of `ORG_CREDENTIAL_ERRORS`.
- `web/tests/vocky-app.test.ts` — new org-credential test suite, `ORG_CREDENTIAL` fixture, rewritten
  duplicate-name test.

Not touched (out of scope, correctly): `web/src/content/landing.ts` (P11's), `web/src/content/project.ts`
(no stale claim in this slice's list), `web/src/app/(app)/projects/[projectId]/actions.ts` (no
plan-scoped change needed there).
