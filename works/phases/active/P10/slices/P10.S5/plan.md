# P10.S5 — CLI parity: org-level keys and Workspace → Org

kind `implementation` · risk **medium** → `slice-executor-mid` · depends `P10.S3`

All paths relative to `/Users/sugang/projects/personal/vocky`. **This slice touches
`src/vocky/cli/**` and `tests/test_cli_*.py` only.**

## Context

The backend and the web app are done. S3 shipped the org routes; S4 shipped the dashboard panel. S5 is
the last middle slice: the CLI must be able to do what the dashboard can.

What you are building against (from `phase.md § P10.S3 landed`):

| route | request | response |
|---|---|---|
| `POST /app/credentials` | optional `{"name"?: string}`, empty body allowed | `201 {credential, key}` |
| `GET /app/credentials` | — | `200 {credentials: [...]}` — **org-level rows only**, oldest-first, incl. revoked |
| `DELETE /app/credentials/{credential_id}` | — | `204`; `400` malformed UUID; `404` otherwise |

**`project_id === null` IS the org-key signal** — no new field, no discriminator. Same
`serialize_credential` payload as a project-bound key.

Out of scope, deferred to **P11** (operator decision 4): `vocky init`, a stored default project,
git-root project derivation, the env-var quickstart. Also out of scope: `docs/cli.md`, `README.md`, and
all durable docs — the review consolidates those.

## Decisions taken at planning (record them in `phase.md`)

**1. Omitting `--project` mints an org key. No `--org` flag.**
`_usage` (`src/vocky/cli/projects.py:195-222`) is the only in-repo pattern for "org-level or
project-scoped", and it works exactly this way: `path = f"/app/projects/{project}/usage" if project else
"/app/usage"`. An `--org` flag would be the CLI's first mutual-exclusion check and would need an
invented error string.

**But the widening must not be silent.** `usage` without `--project` is a wider *read*; `keys mint`
without `--project` is a wider *credential*. So mint prints an explicit scope line — see decision 4,
which is what makes this default safe.

*Counter-argument, record it honestly:* an explicit `--org` would make accidental widening impossible.
Rejected because the printed scope line closes the same gap without inventing an idiom, and existing
`--project` invocations are unaffected either way. Note also that making `--project` optional removes
Typer's exit-2 path for a missing required option — no test asserts it, but an agent script that relied
on that failure would now succeed with a broader key. That is the real cost of this choice; state it.

**2. `keys list` without `--project` lists org keys only.** That is all `GET /app/credentials` returns.
The "where are my other keys?" surprise is real, so **the help text and the empty state must name the
other command explicitly** rather than implying a tenant-wide view.

**3. `keys revoke <ID>` without `--project` → `DELETE /app/credentials/{id}`.** Give the 400-malformed
case a hint, copying the `try/except ApiError` + `exc.status_code` block at
`src/vocky/cli/feedback.py:189-200`. Let 404 surface raw — no command in this CLI translates a 404, and
`docs/cli.md` documents "unknown or cross-tenant id → 404 (never 403)" as the contract.

**4. `keys mint` prints a scope line — before the key.** `docs/cli.md:66` hardens *"prints the plaintext
key exactly once, on its own line (the last line of output)"* as a contract coding agents parse against.
**The key must remain the last line.** Put the scope line with the existing "copy this now" warning.

**5. `vocky signup` mentions the auto-provisioned `"default"` project.** The signup response gained an
additive `project` object, and `src/vocky/cli/auth.py:92` already announces the workspace. Saying a
project was created too is *reporting what happened*, not building onboarding ergonomics — those stay
P11's. One line.

## Scope

### 1. `src/vocky/cli/projects.py` — the `keys` group

`_PROJECT_OPTION` (`:35-40`) becomes optional (`None`, `str | None`), mirroring
`src/vocky/cli/feedback.py:34-39`, which is already an optional `--project` under the same name in a
sibling module. **One edit flips mint, list and revoke together** — that is intended, but it means all
three bodies need their null branch.

- **`_keys_mint` (`:116)`** — `POST /app/credentials` when `project` is `None`, else today's path.
  Print the scope line, then the existing show-once warning, then `result["key"]` **last**.
- **`_keys_list` (`:145)`** — `GET /app/credentials` when `None`. Add scope to the row's **parenthetical
  suffix** beside the existing derived `state` (`:163-172`) — that is where derived state already lives,
  so no structural change and no column alignment needed. Derive it from `project_id`, and see the trap
  below.
  **`:158-160`'s empty-state hint interpolates `--project {project}`** and will literally render
  `--project None` unless it gets a null branch. Fix it, and use it to name the other command
  (decision 2).
- **`_keys_revoke` (`:175)`** — `DELETE /app/credentials/{id}` when `None`, plus the 400 hint.

### 2. The trap — do not let a stub read as an org key

`credential.get("project_id")` returns `None` for **both** "org key" *and* "field absent from a test
stub". The existing mint tests (`tests/test_cli_projects.py:118-128`) return a `credential` object with
**no `project_id` field at all** — so the moment mint or list renders scope, those stubs silently read
as org keys and the tests pass for the wrong reason.

**Give every credential stub an explicit `project_id`.** Consider distinguishing "absent" from `None` in
the rendering code if it is cheap; if not, the explicit stubs are the guard.

### 3. Workspace → Org (12 CLI sites)

**Docstrings are user-visible** — Typer renders them as `--help` text.

- Docstrings/help: `projects.py:27, 55, 83, 201, 210`; `feedback.py:29, 38, 135`; `auth.py:67, 143`
- **Printed stdout:** `auth.py:92` (`A workspace "{name}" was created for you automatically.` — this is
  also where decision 5's project line goes) and `auth.py:157`
  (`label = "Workspace" if len(tenants) == 1 else "Workspaces"`)

Wire identifiers are untouched: `tenant`, `tenants[]`, every route and JSON field keep their names.

Test coupling to check rather than assume: `tests/test_cli_auth.py:51` (a test *name*) and `:64` (the
fixture value `"cli's workspace"`); the assertion at `:77` matches on fixture data, so it likely
survives.

### 4. Style — follow the CLI's conventions, invent nothing

No table library, no shared renderer, no colour on success paths: bare `typer.echo` f-strings, two-space
separators, `—` for absent values, module-local `_date()`. `typer.secho` appears exactly once in the
whole CLI (`context.py:90`, `fail()`) — do not add a second.
`_date()` is already duplicated across `projects.py:43-48` and `feedback.py:60-65`; **duplication is the
accepted local norm here — do not refactor it in this slice.**
`feedback.py:110` shows the existing null-project rendering idiom (`… if project_id else "—"`).

### 5. The lean-CLI invariant

`src/vocky/cli/**` must not import server code or `pip install vocky` breaks silently
(`docs/current/experience.md:320-324`). The only non-`cli` hop is
`src/vocky/cli/client.py:27 → vocky.smoke.make_http_user_agent → httpx`, and `smoke.py`'s module-level
imports are exactly `json, os, time, urllib.request, uuid, httpx` — clean. **Keep it that way; add no
new import outside `typer` / `httpx` / `vocky.cli.*`.**

`src/vocky/smoke.py` also calls `/app/projects/{id}/credentials` and is a tempting place to edit.
**Leave it alone** — it is the deploy smoke's per-project path and is out of scope.

### 6. Tests (`tests/test_cli_projects.py`, `tests/test_cli_auth.py`)

Follow the local conventions: `runner = CliRunner()`, and HTTP stubbed by monkeypatching the **client
factory** (`_stub_api(monkeypatch, handler)` swaps `CliContext.make_client` for one wrapping
`httpx.MockTransport`) — not httpx globally. The helper is copy-pasted per test module; there is no
shared conftest fixture, so use the local copy. Assert method/path/headers inside the handler, then
`result.exit_code` and substring checks on `result.stdout` / `result.stderr`.

Keep it terse (`AGENTS.md`). Cover:

- `keys mint` with no `--project` → `POST /app/credentials`, scope line present, **key is the last line**
- `keys revoke` with no `--project` → `DELETE /app/credentials/{id}`; and the 400 hint
- **`keys list` has no test at all today** — add its first one, with a stub returning one org row
  (`project_id: None`) and one project-bound row, asserting both scope words render
- the existing project-scoped `keys` tests still pass with explicit `project_id` in their stubs
- `signup` announces the org and the default project

## Verification

```bash
make test                            # the repo gate: full pytest suite
uv run vocky --help                  # Typer renders docstrings; eyeball the Org wording
uv run vocky keys --help
python3 scripts/workflow.py validate
```

No linter is configured (`ruff` is not a project dependency — S2 and S3 both confirmed), so `make test`
plus the `--help` eyeball is the gate.

**Also verify the lean-CLI invariant explicitly** and record the result:
`uv run python -c "import vocky.cli.app"` in an environment without the server extra is the ideal check;
if that is not available, grep the transitive imports of `src/vocky/cli/**` and state what you checked.

## Definition of done

`vocky keys mint|list|revoke` work with and without `--project`; the scope is visible in mint and list
output; the key is still the last line of mint output; Workspace → Org is complete across all 12 sites;
signup reports the default project; every credential test stub carries an explicit `project_id`; the
suite passes; `result.md` and the `phase.md` notes are written.

**No `doc-new-version`** — append one-line **Doc impact** notes to `phase.md`. Flag (do not edit)
`docs/cli.md`'s Keys section `:91-97`, its walkthrough `:136-171`, the wording at `:78`/`:81`/`:201`,
and `README.md:78,325`, which hardcode `--project` examples.
