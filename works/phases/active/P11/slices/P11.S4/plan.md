# P11.S4 — Canonical end-user `SKILL.md`, served byte-copy, parity script + first CI workflow

## Why

vocky has **no end-user skill**. All 16 `.claude/skills/*` and 15 `.agents/skills/*` are this repo's own
phase/slice workflow machinery — none mentions capturing feedback, `vk_` keys, or the product API. The
phase's third pillar is an agent skill published on the landing page, so this slice has to **author** it,
then publish it the way knowledge did: a real file served statically, held to the canonical copy by a
**byte-parity gate in CI**.

The three preceding slices made the skill authorable: the hero now depicts the true capture shape (S1),
`vocky capture` + `VOCKY_API_TOKEN` exist (S2), and there is a real install line (S3). This slice writes
the skill **against what actually shipped**, not against a plan.

## Part 1 — the canonical skill

### Home: a new top-level `skills/vocky-feedback/SKILL.md`

Verified free: nothing at the repo root is named `skills` (`git ls-files` top level has no such entry).

**Do not put it under `.claude/skills/` or `.agents/skills/`.** Those are repo-development machinery and
would load into every session in *this* repo. Every existing skill lives under a **dot**-directory, so a
non-dot `skills/` reads as product artifact by contrast, sitting beside `src/`, `web/`, `docs/`. It is also
automatically excluded from the sdist, since `pyproject.toml`'s sdist `include` is root-anchored to
`/src/vocky`, `/README.md`, `/LICENSE` — no packaging change needed.

### Frontmatter — match the in-tree convention exactly

Three fields, in this order, unquoted single-line scalars, `---` delimited:

```
---
name: vocky-feedback
description: <one long line>
allowed-tools: <comma-space inline list>
---
```

- `name:` must equal the directory name.
- **Omit `disable-model-invocation`.** 14 of the 16 repo skills set it; an end-user product skill wants
  model invocation. Its absence is exactly what makes the `description`'s trigger sentence load-bearing.
- The `description` must carry a **hard negative trigger**, the idiom already in-tree at
  `.claude/skills/design-cowork/SKILL.md:3` (`NOT for non-visual "design" …`). Something in the shape of:
  *use when the user wants a piece of product feedback recorded in vocky; **NOT** for general note-taking,
  bug tracking, or anything the user has not asked to send anywhere.*
- `allowed-tools:` is an inline comma-space list with scoped Bash, per `.claude/skills/commit/SKILL.md:4`.
  Scope it tightly — e.g. `Bash(curl:*), Bash(vocky capture:*), Bash(vocky keys:*), Read`.
- Body opens with `# vocky-feedback` as H1 matching `name:`.

### Content — write against the surface that actually shipped

Author it in knowledge's idiom: **exact commands, spelled out to be run verbatim**, rather than rules to
reason from. Numbered H2 steps. Two capture paths, REST primary.

**The two-variable contract** (the phase's headline promise):

```
export VOCKY_BASE_URL="https://vocky.hi2vi.com"
export VOCKY_API_TOKEN="vk_..."
```

Carry the three blockers, which are real and all apply:

1. **A repo `.env` is never auto-loaded** by Claude Code or Codex, and a secret in a repo file risks an
   accidental commit. Recommend `~/.zshenv`: sourced by every zsh invocation, so every Bash call, every
   Codex exec and every repo inherits it, and the key stays out of all repos.
2. **Codex's `workspace-write` sandbox denies outbound network by default** — the POST fails and the skill
   silently degrades. Fix: `[sandbox_workspace_write] network_access = true` in `~/.codex/config.toml`.
   Claude Code needs nothing.
3. Where a key comes from: `vocky keys mint` (its output now ends with an export hint immediately before
   the show-once key line), or the dashboard.

**Path A — the CLI (primary, one command).** Exactly as S2 shipped it:

```
vocky capture "<the user's words>" --product <product> [--value 1|2] [--comment ...] [--tag ...] [--session-id ...] [--user-id ...] [--project ...]
```

- `--product` is the only required option. `--tag` is repeatable and is omitted from the body entirely
  when unused (never sent as `[]`). Pass `-` as the message to read it from stdin instead of fighting
  shell quoting — the right move for multi-line user quotes.
- Success prints exactly: `Captured — request_id <full uuid>`.
- `--project` is honored **only** for an org-level key; a project-bound key ignores it.

**Path B — raw REST**, for an agent with no vocky install. `POST $VOCKY_BASE_URL/api/feedback`,
`Authorization: Bearer $VOCKY_API_TOKEN`, and the **nested** `source` object — the single most important
shape in the whole file:

```json
{
  "message": "…",
  "source": { "product": "checkout-web", "integration": "claude-code" },
  "feedback_value": 2,
  "tags": ["checkout"]
}
```

Write the body to a temp file and `curl --json @file` rather than passing it as a shell argument — that
keeps quotes, newlines and Korean text out of argv, and mirrors how knowledge's skill does it.

Success is **`202`** with exactly `{"request_id", "accepted_at", "status": "accepted"}`.

**Path C — `/mcp`, mentioned as an alternative transport, not documented in depth.** One short section:
the endpoint is a single POST-able `https://<host>/mcp` (FastMCP Streamable-HTTP, stateless, JSON
responses), the same `vk_` bearer guards the whole transport including `initialize`, and the one tool is
`capture_feedback` taking the same nested `source`. Give the client-config one-liner
(`claude mcp add --transport http vocky <url>/mcp --header "Authorization: Bearer $VOCKY_API_TOKEN"`) and
one line on the self-hosting gotcha: DNS-rebinding protection allows only localhost by default, so a
self-hosted origin needs its hostname in `VOCKY_MCP_ALLOWED_HOSTS`. `attachment_ids` is REST-only.

**Error handling — branch by branch, verified against source and tests.** Every failure body is a flat
`{"detail": "<string>"}`; there are no error codes and no `request_id` on failures:

| Status | `detail` | What the skill should do |
|---|---|---|
| `401` | `Unauthorized` (+ `WWW-Authenticate: Bearer`) | The key is wrong or revoked. Say so, name `VOCKY_API_TOKEN`, **stop** — never retry, never fall back. |
| `400` | `request body must be valid JSON` / `request body must be a JSON object` | Our payload is malformed. Fix once and retry once. |
| `400` | `<dotted.loc>: <pydantic msg>` — e.g. `source.product: Field required` | A schema violation. **Only the first pydantic error is reported**, so fixing one may reveal another. |
| `400` | `message must not be blank` / `source.product must not be blank` | Both are required non-blank. |
| `400` | `channel must be one of: web, mobile, support`, `project must not exceed 200 characters`, … | Semantic normalization failures; the `detail` is actionable verbatim. |
| `503` | `capture queue unavailable` | Transient. Report it; do not silently drop the user's feedback. |
| `500` | `project resolution failed` / `credential scope unavailable` | Server-side. Report verbatim, do not retry. |

For the CLI path: **exit code is `1` for every failure** and does not encode the HTTP status; stderr is the
server's `detail` verbatim, except `401`, which is remapped to
`Unauthorized — check VOCKY_API_TOKEN (the key may be wrong or revoked).`, and a missing env var, which is
`VOCKY_API_TOKEN is not set — mint a key with \`vocky keys mint\` and export it.` with no HTTP call made.
Transport failure is `Could not reach vocky at <base_url> (<exc>).`

Include a **verify/health snippet** the user can run to confirm the two exports work before capturing
anything, and a final **Report** step telling the agent what to tell the user (captured vs not, and the
`request_id`).

### Length and register

Aim for a focused document — knowledge's is 486 lines because it also writes an HTML explainer; this one
captures one thing and should be considerably shorter. Do not pad. Every command must be one the reader
can paste.

## Part 2 — publish it

Commit `web/public/SKILL.md` as a **byte-identical** copy of `skills/vocky-feedback/SKILL.md`. Not
generated at build time — a committed copy defended by a gate, which is cheap and auditable.

### The prettier collision — handle it, do not discover it later

`web/.prettierignore` currently ignores only `pnpm-lock.yaml`, `.next/`, `out/`, `build/`, `node_modules/`
— **not `public/`**. Prettier formats markdown, so the moment anyone runs `prettier --write .` in `web/`,
markdown reflow would rewrite `web/public/SKILL.md` and **break byte parity**. Add `public/` to
`web/.prettierignore`. This is a required part of the slice, not an optional tidy.

## Part 3 — the parity gate

`scripts/skill_parity.py`, stdlib-only, following `scripts/wait_for_health.py`'s conventions:
`#!/usr/bin/env python3`, `from __future__ import annotations`, a module docstring that **is** the spec, a
`main()`, and **the exit code is the contract** (`0` pass, `1` fail).

It compares exactly two files, **full-file bytes including frontmatter** — the served copy is a straight
publish, not a reframed derivation, so nothing is allowed to differ:

- `skills/vocky-feedback/SKILL.md` (canonical)
- `web/public/SKILL.md` (served)

Two failure modes, both `FAIL —` prefixed and exit `1`: a missing file (name which), and a byte mismatch
(say plainly that `web/public/SKILL.md` is not a byte-for-byte copy of the canonical, and how to fix it —
copy the canonical over it). Success prints one `PASS —` line.

Add a `.PHONY` Makefile target following the file's conventions (`Makefile:19,40-41`), e.g.
`check-skill-parity`, invoked as `python3 scripts/skill_parity.py` — note this script needs **no** `uv
sync`, unlike `wait_for_health.py`'s `uv run python` form, so plain `python3` is correct and is what CI
will use.

## Part 4 — the first CI workflow

Create `.github/workflows/ci.yml`. **This is the repo's first push/PR gate** — `deploy-production.yml` is
`workflow_dispatch`-only and nothing has ever run on a push.

### It must be green on arrival — verified today

| Check | Status right now | In CI? |
|---|---|---|
| `pnpm lint` | exit 0, clean | **yes** |
| `pnpm typecheck` | exit 0, clean | **yes** |
| `pnpm test` | 61 passed | **yes** |
| `python3 scripts/skill_parity.py` | new, will pass | **yes** |
| `bash -n web/public/install.sh` | exit 0 | **yes** — cheap, mirrors the deploy workflow's "Validate deploy helpers" precedent |
| `pnpm exec prettier --check .` | **exit 1 — 12 pre-existing failures** | **NO** |
| `uv run pytest` | **88 passed / 121 errors without Postgres** | **NO** — P12 adds it with a service container |

**Do not add `format:check`** and **do not** fix the 12 pre-existing prettier failures here — that is a
12-file diff in files this slice has no business touching. **Do not add a pytest job**; the phase
explicitly leaves it to P12, and a bare runner has no Postgres. Record both exclusions in `result.md` and
in `phase.md` so the review does not read them as oversights.

### Shape — mirror `deploy-production.yml`'s house style

- A header comment block above `on:` explaining the workflow's role.
- `on: push: branches: [main]` **and** `pull_request:`; top-level `permissions: contents: read`.
- `runs-on: ubuntu-latest`, human `name:` in Title Case per job, sentence-case step names, `shell: bash`
  with `set -euo pipefail` on inline scripts.
- `actions/checkout@v4` (the version already used in this repo).
- Node **22** and pnpm **10.28.2**, matching `web/package.json` (`engines.node >=22.13.0`,
  `packageManager`), `web/.nvmrc` (`22`), and `web/Dockerfile:11,17`. The repo's existing precedent is
  **corepack** (`corepack enable && corepack prepare pnpm@10.28.2 --activate`), which matches the
  Dockerfile exactly — prefer it over `pnpm/action-setup`. Install with `pnpm install --frozen-lockfile`,
  as the Dockerfile does.
- Shape it so **P12 adds a job** rather than starting from nothing.

**Note and verify**: nobody has confirmed `pnpm install --frozen-lockfile` succeeds from a clean checkout
against the committed `web/pnpm-lock.yaml` — local `node_modules` was already warm. Check it here (see
validation) rather than letting CI discover it.

## Validation

1. `python3 scripts/skill_parity.py` → `PASS`, exit 0.
2. **Prove the gate actually fails**: append a byte to `web/public/SKILL.md`, re-run → `FAIL`, exit 1,
   then restore and re-run → `PASS`. A gate never seen red is not a verified gate.
3. `cmp skills/vocky-feedback/SKILL.md web/public/SKILL.md` → identical.
4. `make check-skill-parity` → passes.
5. From `web/`: `pnpm lint`, `pnpm typecheck`, `pnpm test` → all exit 0, 61 tests. Adding files to
   `public/` must not change the app build.
6. `pnpm exec prettier --check .` from `web/` → still exactly the same **12** pre-existing failures, and
   **`public/SKILL.md` is not among them** (proves the `.prettierignore` addition works).
7. **Clean-checkout lockfile check**: in a temp clone or with `node_modules` moved aside, run
   `pnpm install --frozen-lockfile` in `web/` → exit 0. If it fails, that is a CI blocker; report it rather
   than papering over it with `--no-frozen-lockfile`.
8. `bash -n web/public/install.sh` → exit 0.
9. **Lint the workflow YAML**: `python3 -c "import sys,yaml" 2>/dev/null` may be unavailable — if PyYAML is
   not importable, at minimum confirm the file parses with
   `uv run python -c "import yaml,pathlib;yaml.safe_load(pathlib.Path('.github/workflows/ci.yml').read_text());print('yaml ok')"`.
   If neither works, say so plainly rather than claiming it was validated.
10. `uv run pytest -q` → unchanged from the S2/S3 baseline (this environment has a live Postgres, so expect
    ~209 passed / 0 errors; establish the delta by comparison, not by assuming a number).
11. `python3 scripts/workflow.py validate` → passes.

**State plainly what was NOT proven**: the workflow has never executed on a GitHub runner (it cannot,
until it is pushed — and GitHub `main` is 45 commits behind), and `/SKILL.md` has never been fetched from a
live origin. Both land in P12.

## Doc impact

Append **one line** to the `## Doc impact` section of `works/phases/active/P11/phase.md` — this changes
durable truth in several places (a published end-user skill, the first CI gate, the two-variable agent
contract). Name the affected docs (`experience`, `product`, `operations`, and `qa` if the CI gate belongs
there) for the review to consolidate. Do **not** run `doc-new-version` and do **not** edit
`docs/current/*.md`.

## Hand-off to P12 — append to `phase.md`

- **Armed flip probe**: `curl -sS -o /dev/null -w '%{http_code}' https://vocky.hi2vi.com/SKILL.md` → `404`
  today, must be `200` after the first deploy, and the served bytes must `cmp` clean against the canonical.
- P12 extends `ci.yml` with the Postgres-backed pytest job (service container), and may separately decide
  whether to fix the 12 prettier failures and add `format:check`.

## Out of scope

- The landing page's skill **section** — designed in `P11.S5`, built after `P11.DECOMP2`. This slice ships
  the file and the gate, **no web UI**.
- No `format:check` in CI, no fixing the 12 pre-existing prettier failures.
- No pytest job.
- No backend change, no `doc-new-version`, no push, no deploy.

## When done

Write `works/phases/active/P11/slices/P11.S4/result.md` from scratch (free-form): the skill's final path
and length, the parity gate's red-then-green proof, the CI workflow's job/step list with the two
deliberate exclusions and why, verbatim validation output, and what was not proven. Append durable
cross-slice notes to `works/phases/active/P11/phase.md` — the `P11.S5` design handoff will ground the
skill-preview pane in this exact file, so record its **path, byte size, line count, and section headings**.
Do not commit and do not change any slice or phase status.
