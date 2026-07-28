# P10.S5 result — CLI parity: org-level keys and Workspace → Org

## What landed

`src/vocky/cli/projects.py`'s `keys` group (`mint` / `list` / `revoke`) now works with or
without `--project`, exactly mirroring the S3 route shapes recorded in `phase.md`:

- **`_PROJECT_OPTION`** (`projects.py:36-41`) is now optional (`None`, `str | None`), mirroring
  `feedback.py`'s existing optional `--project`. One edit flips all three `keys` commands, as the
  plan called out.
- **`_keys_mint`** — `project is None` → `POST /app/credentials`; else the existing
  `POST /app/projects/{project}/credentials`. A `Scope: this project only.` /
  `Scope: your whole org.` line prints with the existing "copy this now" warning, **before** the
  key. The plaintext key is still the strict last line of output — verified both by eyeball
  (`uv run vocky keys mint --project p1`-style manual read) and by test assertion
  (`result.stdout.rstrip("\n").splitlines()[-1] == "vk_..."`), not merely a substring check as the
  old test did.
- **`_keys_list`** — `project is None` → `GET /app/credentials` (org rows only). The empty-state
  hint got a null branch: `--project` present → the old `vocky keys mint --project {project}`
  hint; `--project` absent → a new hint that names `vocky keys mint` and explicitly points at
  `vocky keys list --project <PROJECT_ID>` for project-scoped keys (decision 2 — "where are my
  other keys?" is answered explicitly rather than implying a tenant-wide view). Verified the
  `--project None` bug the plan flagged does **not** appear (`test_keys_list_empty_org_hint_names_project_scoped_command`
  asserts `"--project None" not in result.stdout`). Scope (`project` / `org`) was added to the
  existing derived-state parenthetical, driven off `credential.get("project_id") is not None` —
  no structural change, no column alignment.
- **`_keys_revoke`** — `project is None` → `DELETE /app/credentials/{id}`, with a 400-malformed-id
  hint copied from `feedback.py`'s `try/except ApiError` + `exc.status_code` pattern (added only on
  the org-level branch, matching the plan's decision 3 wording). 404 is left to surface raw — no
  hint, matching `docs/cli.md`'s published 404-never-403 contract (not edited this slice, flagged
  for the review per plan scope).

**The trap avoided.** Every credential stub across `tests/test_cli_projects.py` now carries an
explicit `project_id` (`"p1"` or `None`) — none rely on the field being merely absent, which would
have silently read as an org key the moment scope rendering landed. New tests were added rather
than only patching existing stubs, since `keys list` had no test at all before this slice.

**Workspace → Org, all 12 sites** (verified by `grep -rn -i workspace src/vocky/cli/` returning
nothing after the edit):
- `projects.py:27` (`projects_app` help), `:55`/`:83` (docstrings), `:201`(now `:239`)/`:210` (now
  `:248`) (`_usage` help/docstring — line numbers shifted slightly from the plan's citation because
  of the intervening edits, content matches exactly).
- `feedback.py:29`/`:38`/`:135` (module help, `_PROJECT_OPTION` help, `_feedback_list` docstring).
- `auth.py:67` (`_signup` docstring), `:92` (printed stdout, now "An org ... was created for you
  automatically." plus a new one-line project announcement per decision 5), `:143` (`_whoami`
  docstring), `:157` (`Workspace`/`Workspaces` → `Org`/`Orgs` label).

Wire identifiers (`tenant`, `tenants[]`, every route/JSON field) are untouched — confirmed by
re-reading every edit: no route string, no dict key, no field name changed, only literal English
words in help text, docstrings, and `typer.echo` strings.

**Test coupling checked, not assumed** (plan's explicit ask): `tests/test_cli_auth.py:51`'s test
*name* was renamed (`test_signup_stores_token_and_reports_workspace` →
`test_signup_stores_token_and_reports_org_and_default_project`) since it now also asserts the
project line; the fixture value `"cli's workspace"` was left exactly as-is (it's the
server-generated friendly org name, which literally contains the word "workspace" per the phase's
decision 3 — unrelated to the product-facing "Workspace" label rename) and a comment records why.
The assertion that matched fixture data survived unedited, as the plan predicted, and a new
assertion (`'"default" project was created too.' in result.stdout`) was added, with the signup
handler's stub gaining an additive `"project": {"name": "default"}` object to match the real S1
response shape.

## Style

No table library, no shared renderer, no new `typer.secho` call (`context.py:90`'s `fail()` is
still the only one). `_date()` was left duplicated across `projects.py` and `feedback.py`, per the
plan's explicit "accepted local norm — do not refactor" instruction. `feedback.py:110`'s
`… if project_id else "—"` idiom was referenced as precedent, not touched.

## The lean-CLI invariant

No import outside `typer` / `httpx` / `vocky.cli.*` was added anywhere in `src/vocky/cli/**`.
Verified two ways:

1. `grep -n "^import\|^from" src/vocky/cli/{projects,feedback,auth,client,context,config_store,app}.py`
   — the only non-`vocky.cli.*` imports besides stdlib/`typer`/`httpx` are `client.py:27`'s
   pre-existing `from vocky.smoke import make_http_user_agent`.
2. **The ideal check the plan asked for, actually run**: built a throwaway venv
   (`python3 -m venv`), `pip install --no-deps -e .` plus only the bare `dependencies` group
   (`httpx>=0.28.1,<1.0.0`, `typer>=0.27.0` — no `server` extra), then
   `python -c "import vocky.cli.app"` → `IMPORT OK`. This is exactly the `pip install vocky`
   scenario the invariant protects, confirmed after this slice's edits, not merely asserted from
   the source tree.

`src/vocky/smoke.py` was read but not edited, per the plan's explicit "leave it alone" — its
`/app/projects/{id}/credentials` path is the deploy smoke's per-project concern and out of scope.
`docs/cli.md` and `README.md` were read but not edited — flagged below for the review to
consolidate (decision 4 is what makes the widening safe: the printed scope line, not silence).

## Validation run

```
$ make test                                    # 206 passed
$ uv run vocky --help                           # eyeballed — Org wording throughout
$ uv run vocky keys --help                      # eyeballed
$ uv run vocky keys mint|list|revoke --help      # eyeballed — no exit-2 on missing --project now
$ python3 scripts/workflow.py validate           # "Workflow validation passed."
```

Plus the lean-CLI invariant venv check described above (`IMPORT OK`).

## Deviations from `plan.md`

None. Every scoped item (the three `keys` bodies, the 12 Workspace→Org sites, the empty-state null
branch, the credential-stub trap, the tests, the lean-CLI verification) was implemented as
described. Line-number citations in this file differ slightly from the plan's for `_usage`
(`:201`/`:210` → `:239`/`:248` after the preceding edits shifted the file) — same content, not a
scope change.

## Doc impact (appended to `phase.md`, not versioned here)

No `doc-new-version` was run. See the `phase.md` "Doc impact" section appended by this slice for
the running list `P10.REVIEW` must consolidate, including the flagged-not-edited
`docs/cli.md`/`README.md` sites.
