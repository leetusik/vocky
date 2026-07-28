# Phase P11: Frictionless onboarding: working install, env-var quickstart, agent skill on the landing

_Intent: see [intent.md](intent.md)._

## Objective

Make vocky's onboarding real end to end for a coding agent: ship an install path for the `vocky` CLI that actually runs from the landing page (publish to PyPI or serve a `curl | bash` installer), add the missing `VOCKY_API_TOKEN` so two environment variables are the whole agent contract alongside today's `VOCKY_BASE_URL`, publish a copyable and downloadable end-user `SKILL.md` on the landing behind a byte-parity CI gate, and correct the landing's untrue hero payload (top-level `source_product` -> nested `source.product`, and the non-existent `vk_live_` prefix). Any net-new landing section goes through a design-cowork gate; no new backend capture contract.

## Context

### Why this phase exists — the onboarding story is not real today

- The `vocky` CLI **cannot be installed** except from a checkout (`docs/cli.md:9-19`, `README.md:48-63`).
- **`VOCKY_API_TOKEN` does not exist anywhere in the tree.** A grep over `src/vocky/**` finds exactly
  five env reads: `cli/context.py:76` (`VOCKY_BASE_URL`), `cli/config_store.py:32,36`
  (`VOCKY_CONFIG_DIR`, `XDG_CONFIG_HOME`), `smoke.py:20,187` (`VOCKY_HTTP_USER_AGENT`,
  `VOCKY_BASE_URL`). The CLI is session-token-only and **has no capture command at all**, so a `vk_`
  key has no CLI consumer.
- There is **no end-user skill**. All 16 `.claude/skills/*` and 15 `.agents/skills/*` are repo-workflow
  machinery; none mentions capturing feedback.
- The hero publishes **two falsehoods** in `web/src/content/landing.ts`.

### Operator decisions (2026-07-29) — build around these, do not relitigate

1. **Install = `curl | bash`, not PyPI.** Ship `web/public/install.sh`. **No `uv publish` in P11**; the
   P6.S9 publish hand-off stays unexercised and `dist/`'s `0.1.0` artifacts stay stale.
2. **Add `vocky capture`.** `VOCKY_API_TOKEN` gets a first-class CLI consumer — a new capture command
   POSTing to `/api/feedback` with the `vk_` key.
3. **CI gate = a new minimal `.github/workflows/ci.yml`** on push + pull_request (parity script + web
   lint/typecheck/vitest). P12 later extends that same file with the Postgres pytest job.

### The honesty problem the `curl` choice creates — and why it is resolved

A hero line naming `https://vocky.hi2vi.com/install.sh` 404s today. It is **not** a live falsehood,
because **the site itself is not deployed** (`docs/current/experience.md:14`; the only workflow,
`.github/workflows/deploy-production.yml`, is `workflow_dispatch`-only and has never run). The landing
page and `install.sh` therefore go live **in the same P12 bring-up**, so no live landing ever serves a
dead command. See "Hand-off to P12" below for the armed flip probes. **Every P11 `result.md` must say
plainly what was *not* behaviorally proven.**

## Decomposition

**This is a design-bearing phase, so it decomposes in two passes** (`design-cowork`). This `DECOMP`
created only the groundwork slices, the design slice, and `P11.DECOMP2`, and records a **build
inventory** (below) instead of build slices. The design decides what gets built; `P11.DECOMP2` cuts the
build slices once the design has landed.

| Slice | Order | Kind | Risk | Depends on | Name |
|---|---|---|---|---|---|
| `P11.S1` | 1 | implementation | low | — | Landing hero honesty: nested `source.product` + real `vk_` key shape |
| `P11.S2` | 2 | implementation | medium | — | CLI: `VOCKY_API_TOKEN` resolution + `vocky capture` over `/api/feedback` |
| `P11.S3` | 3 | implementation | medium | — | `curl \| bash` installer: `web/public/install.sh` |
| `P11.S4` | 4 | implementation | medium | `P11.S2` | Canonical end-user `SKILL.md`, served byte-copy, parity script + first CI workflow |
| `P11.S5` | 5 | **co-work** | high | `P11.S4` | Design round 02: hero install row, agent env-var quickstart, skill-on-landing |
| `P11.DECOMP2` | 6 | decomposition | high | `P11.S5` | Decompose the build from the landed design |

### Ordering rationale

- **S1 first, and specifically before the design gate.** Claude Design **reads the real repo**, so the
  hero must be truthful before the handoff — otherwise the round is designed around a lie.
- **S2 before S4**: the skill documents `vocky capture`, so the command must exist first.
- **S3 before S4**: the skill's install section quotes the real installer line.
- **S4 before S5**: `design-cowork` requires grounding in **real content, never lorem** — a skill-preview
  pane cannot be designed against a file that does not exist. This is the one place vocky's order differs
  from knowledge's P20 (whose skill already existed under a parity gate).
- **S5 → DECOMP2**: the design decides what gets built; build slices are cut only from the landed design.

### Risk ratings (the phase's main cost lever)

- **S1 `low`** — a fully mechanical, fully specified content edit in one file. The only slice that is.
- **S2/S3/S4 `medium`** — real judgment (CLI UX and error mapping, `curl | bash` safety, skill authoring,
  the repo's first CI workflow) but no architectural risk. Routes to `slice-executor-mid`.
- **S5 `high`** — `design-cowork` forbids ever rating a design slice `low`. Never dispatched (no executor
  has `DesignSync`); the orchestrator runs it inline on the main thread.

### Slice intents

These are **intents for the orchestrator to plan at each slice's turn** — not plans. No `plan.md` was
pre-filled; every new slice folder holds only `slice.json`.

- **S1 — Hero honesty.** In `web/src/content/landing.ts`: `:57` `vk_live_9f3c…` → a `vk_`-shaped stub
  matching `"vk_" + secrets.token_urlsafe(32)`; the `:58-64` body's top-level
  `"source_product": "checkout-web"` (`:59`) → nested `"source": { "product": "checkout-web" }`; and
  correct the false rationale comment at `:11-13`. No component edit — `hero.tsx` is untouched (it only
  interpolates `hero.request.auth` / `.body` at `:27-30`). **Copy inside an already-designed component is
  not a design round** (the line knowledge drew crisply). Verify with `pnpm typecheck && pnpm test`.
  *Verified caveat:* the hero body's other fields (`message`, `feedback_value`, `target_type`, `tags`) are
  all **valid top-level** capture fields (`capture.py:34-57`) — only `source_product` is wrong. Do not
  touch them.
- **S2 — CLI capture.** `VOCKY_API_TOKEN` in `cli/context.py` beside `VOCKY_BASE_URL`, and a new
  `cli/capture.py` registered in `app.py`. Precedence to settle at plan time (`--token` > env > stored?);
  the key is a `vk_` credential, **never** the session token, and the two must not be conflated in the
  config store. Build the nested `source` correctly; surface the 202 `request_id`; map `401` to "check
  `VOCKY_API_TOKEN`" (not "run `vocky login`"). **Keep imports lean** — typer/httpx/stdlib only. Consider
  a version bump off the stale `0.1.0` (`pyproject.toml:7`), since the installer prints `vocky --version`.
  Terse tests only.
- **S3 — Installer.** `web/public/install.sh`, mirroring knowledge's verified 50-line shape:
  `set -euo pipefail`; **every statement inside `main()` with `main "$@"` as the final line**, so a
  truncated `curl | bash` can never half-execute; bootstrap `uv` via the Astral installer only if absent
  and echo before doing it; `uv tool install --reinstall git+https://github.com/leetusik/vocky` for
  idempotent, upgrade-safe re-runs; no sudo, nothing system-wide (`$HOME/.local/bin`); PATH-tolerant
  verification that warns rather than dies; close by printing the next command. vocky's CLI is at the
  **repo root**, so there is **no `#subdirectory=` fragment** — and the lean/`server`-extra split means a
  default git install already pulls only httpx + typer. Verify: `bash -n`, plus a real run in an isolated
  temp `HOME` against a **local** install target. State plainly that the live `404 → 200` flip is P12's.
- **S4 — Skill + parity + CI.** Author the canonical end-user `SKILL.md` (capture over REST with `curl`,
  and the `vocky capture` one-liner; `/mcp` noted as the alternative transport). **Do not put it under
  `.claude/skills/` or `.agents/skills/`** — those are this repo's own workflow machinery and would load
  into every session here; recommend a new top-level `skills/<name>/SKILL.md`, decided at plan time.
  Mirror knowledge's authoring idiom: exact commands spelled out to run verbatim, branch-by-branch error
  handling (`202` / `400` / `401` / `503` / transport), a hard negative trigger in the frontmatter
  `description`, and a scoped `allowed-tools` allowlist. Then commit `web/public/SKILL.md` as a
  **byte-identical** copy, add `scripts/skill_parity.py` (stdlib-only, exit code is the contract —
  matching `scripts/wait_for_health.py` convention) plus a `Makefile` target, and create
  `.github/workflows/ci.yml` on push + pull_request running the parity script and web
  lint/typecheck/vitest. **Leave the Postgres pytest job to P12** — but shape the file so P12 adds a job
  rather than starting from nothing.
- **S5 — Design round 02 (`co-work`).** Orchestrator-run **inline on the main thread**; never dispatched.
  Writes `docs/reference/design/rounds/02-onboarding/handoff.md` only — **zero implementation code** —
  then `pending`, then read-back with `DesignSync`, land as-is, SIGNOFF. Target the design project **by
  id** `1eaa0803-46e3-426a-ab04-17a802170234`. The handoff must require **one card per reviewable unit**
  with the line-1 `@dsCard` marker, plus `result.md` and `build-prompt.md`; carry the three env-var
  blockers (below) as content to surface; state round 01's brand as **locked**; and **pose every open
  question back** rather than answering it.
- **`P11.DECOMP2`** — cuts the build slices from the landed design and `build-prompt.md`, at orders after
  its own: backing work first, the design implementation after, then any fidelity fix.

## Build inventory (what to build, not how)

This is what the S5 handoff's scope checklist is written from. **The design is free to add to it and cut
from it** — that is exactly why the build slices are not cut yet.

1. **Hero install command row** — the `curl | bash` line, copyable, in the hero's left column.
2. **Agent quickstart section** — the two-env-var contract (`VOCKY_BASE_URL` + `VOCKY_API_TOKEN`) as the
   recommended agent path: the `~/.zshenv` block, the Codex `network_access` trap, and a verify/health
   snippet with success and failure legends.
3. **Skill-on-landing section** — a preview pane over the served `/SKILL.md` (build-time `fs` read of the
   **served** copy, so the preview can never fork from the gated artifact), **Copy the skill** (fetching
   the served file rather than embedding a fork), and **Download** as a plain
   `<a href="/SKILL.md" download>`.
4. Consequent **nav / `SectionId` additions** (`web/src/content/section-ids.ts`) and any `LandingNav`
   entry.

**Apply-time note for `DECOMP2`'s slices:** copy payloads should be **byte-locked constants with display
deliberately separate from clipboard bytes**, guarded by a vitest that re-spells them — vocky has no such
test today (none of the 61 existing tests asserts a copy constant), and it would be the first.

## Findings & Notes

_Durable findings and cross-slice notes; `DECOMP` seeded this, and each slice appends when it finishes._

### Capture contract (verified against `src/vocky/capture.py`, `auth.py`, `app_api.py`)

- `POST /api/feedback` requires `message` (`capture.py:37`) and nested `source: {product, integration?}`
  (`capture.py:27-31`, field at `:38`); `source.product` must be non-blank — `require_non_blank(
  raw.source.product, "source.product")` at **`capture.py:275`**. REST-only extras `attachment_ids` and
  `project` (org-key destination, default `"default"`, `capture.py:80-81`, resolver at `:325-362`).
  Response **202** `{request_id, accepted_at, status:"accepted"}` (`capture.py:84-89`).
- All other hero-body fields are legitimate top-level capture fields (`capture.py:34-57`:
  `feedback_value`, `comment`, `channel`, `target_type`, `tags`, …). **Only `source` is nested.**
- Auth is **`Authorization: Bearer vk_…`**, not `X-API-Key` (`auth.py:66-81` extracts the bearer;
  middleware at `:144-215`). The same middleware guards `/api/*` **and** `/mcp`
  (`auth.py:171-174`), so a `vk_` key drives both; the single MCP tool is `capture_feedback`
  (`src/vocky/tools/capture_feedback.py:36-37`).
- **`vk_` is never validated as a prefix** — the middleware resolves the credential purely by
  `sha256_hex(token)` at **`auth.py:183`**. Keys are minted as `f"vk_{generate_opaque_token()}"`
  (`app_api.py:241` project-scoped, `:320` org-scoped). There is **no `vk_live_` / `vk_test_` tier.**
- A `vk_` key authorizes **only** `/api/*` + `/mcp`. Every existing CLI command talks to `/app/*` with a
  **session** token — which is exactly why `VOCKY_API_TOKEN` needs `capture` to have any consumer.
- **A working reference payload already exists in-tree**: `src/vocky/smoke.py:112` posts
  `"source": {"product": "vocky-smoke", "integration": "make-smoke"}` to `POST /api/feedback` and asserts
  the 202 `{request_id, status:"accepted"}` — the exact shape S1's hero must depict and S2's `vocky
  capture` must build. `smoke.py:141`'s top-level `source_product` is the **read** filter on
  `GET /api/feedback` (verified in context), which is why the two shapes legitimately differ.

### CLI (verified against `src/vocky/cli/`)

- `context.py:66-84` base-URL precedence `--base-url` > `VOCKY_BASE_URL` > stored > `http://127.0.0.1:8000`;
  `authed_client()` (`:61-62`) hard-fails "Not signed in — run `vocky login`."  `client.py:103-106`
  already injects `Authorization: Bearer` (and accepts an explicit `token=` override), so a `vk_` path
  **reuses `ApiClient` unchanged**.
- `config_store.py:25-40` — `VOCKY_CONFIG_DIR` > `$XDG_CONFIG_HOME/vocky` > `~/.config/vocky`;
  dir `0700` / file `0600`, keys `token` + `base_url` only (`:66-91`).
- Existing CLI modules: `app.py`, `auth.py`, `client.py`, `config_store.py`, `context.py`, `feedback.py`,
  `projects.py`. `capture.py` is net-new.
- **Import isolation is load-bearing** (`docs/current/operations.md:124`): `vocky.cli.*` may import only
  typer / httpx / stdlib / the httpx-only `vocky.smoke`. A server-side import silently breaks the lean
  install. Guard: `uvx --from dist/*.whl vocky --version`.
- No linter/formatter is configured for Python.
- `pyproject.toml:7` still reads `version = "0.1.0"`; `dist/` holds the stale `vocky-0.1.0-py3-none-any.whl`
  + `.tar.gz` from P6.S9.

### Web / serving (all verified)

- `web/public/` exists but holds only `.gitkeep`. `web/next.config.ts:55` `output: "standalone"`;
  `web/Dockerfile:40` `COPY --from=build /app/public ./public`; `deploy/vocky.conf:282-288` is a bare
  `location / { proxy_pass http://$vocky_web:3000; }`. The only other `location` blocks are `/api/`,
  `/api/auth/`, `/api/app/`, `/auth/`, `/app/`, `= /healthz`, `/mcp`, and `/admin/` (a `return 404`) —
  **none shadows a root-level static path**. → `web/public/install.sh` and `web/public/SKILL.md` serve at
  `/install.sh` and `/SKILL.md` with **zero infra work**. Caveat: `X-Content-Type-Options: nosniff` is
  global (`next.config.ts:43`), so a browser will *download* `.md` rather than render it — fine for
  `<a download>`; a route handler would be needed only for in-browser viewing.
- Landing composition: `web/src/app/page.tsx:32-46` → `LandingNav`, `Hero`, `TrustStrip`, `HowItWorks`,
  `Showcase`, `Features`, `Pricing`, `ClosingCTA`, `LandingFooter`. Hero snippet assembled at
  `hero.tsx:27-30` from `LANDING.hero.request`; right column is `EndpointCard` (`hero.tsx:72-74`).
- **Copy-as-data is a house rule** — components hold no literal copy; everything lives in
  `web/src/content/` (`docs/current/frontend.md:272`). Section anchors are typed: `SECTION_IDS` map at
  `web/src/content/section-ids.ts:8-13` (today only `features`, `how`, `pricing`), `SectionId` type at
  `:15`. A new section **must** add its id there.
- Existing primitives to reuse, not rebuild: `web/src/components/ui/endpoint-card.tsx` (`<pre>` in a
  forest panel), `web/src/components/show-once-key.tsx:41-48` (a working
  `navigator.clipboard.writeText` + permission-denied fallback — the copy mechanics to extract; note it
  lives directly under `components/`, **not** under `ui/`), `ui/reveal.tsx`, `ui/section.tsx` CVA tones.
- **`source_product` is correct on the read path** — `web/src/app/(app)/feedback/*`,
  `web/src/lib/vocky/types.ts:231,329`, and `src/vocky/smoke.py:141` (a query filter). **Only the capture
  request is nested.** Do not "fix" those.
- Tests: vitest, `environment: "node"`, `include: ["tests/**/*.test.ts"]` (`web/vitest.config.ts:30-33`);
  5 files (`auth-routes`, `session-guards`, `session`, `vocky-app`, `vocky-auth`), **61 tests**, none
  asserts a copy constant. No jsdom/RTL — so testable logic must be extracted into pure helpers.
  `web/.dockerignore:9` excludes `tests`, so a parity gate runs in CI, never in the image.

### Design

Round 01 (`docs/reference/design/rounds/01-brand-app-landing/`) designed the brand + landing;
`SIGNOFF.md:10` records design project **`1eaa0803-46e3-426a-ab04-17a802170234`** (target by **id**),
30 cards, token delta applied by P9. Tokens live in `web/src/app/globals.css`; the applied system is
documented at `docs/current/frontend.md:84-89,229-231,269-270`. **The next round is 02** —
`docs/reference/design/rounds/` holds only `01-brand-app-landing` today. Round 01's brand is **locked**
for round 02.

### The `git+` shipping caveat (knowledge lost real time to this)

`uv tool install git+https://github.com/leetusik/vocky` installs whatever is on **GitHub `main`**, so
P11's `vocky capture` is unreachable to installer users until an operator-gated `git push`. The
workspace never pushes unasked. → P11 verifies the installer against a **local** target in an isolated
temp `HOME`, and hands the real push + live proof to P12.

### Three env-var blockers knowledge documented — all apply, all belong in the S5 design handoff

1. A repo `.env` is **never** auto-loaded by Claude Code or Codex, and a secret in a repo file risks an
   accidental commit → recommend `~/.zshenv`.
2. Codex's `workspace-write` sandbox **denies outbound network by default** →
   `[sandbox_workspace_write] network_access = true` in `~/.codex/config.toml`. Claude Code needs nothing.
3. Cloudflare was empirically **not** a barrier for knowledge — but vocky's site is not live, so the probe
   **cannot run in P11**. Record it as a P12 check; do not design around an unverified blocker.

### Citation corrections made by `DECOMP` (plan facts that did not survive verification)

The `P11.DECOMP` plan's "Grounded facts" were spot-checked line by line against the tree. Four citations
were off; the **claims were all correct**, only the line pointers moved. Corrected above and repeated
here so no later slice re-derives them:

1. `auth.py:130-133` (cited for "`vk_` is never validated as a prefix") is a docstring about per-request
   project-scope caching. The real evidence is **`auth.py:183` — `sha256_hex(token)`** inside
   `ProjectCredentialAuthMiddleware.__call__` (class at `auth.py:144`). Claim stands: no prefix check
   anywhere.
2. `capture.py:274` (cited for the `source.product` non-blank guard) is the **`message`** guard;
   `source.product` is at **`:275`**. And the nested `source` **field** is declared at `:38`, not `:37`
   (`:37` is `message: str`).
3. `section-ids.ts:8-13` is the `SECTION_IDS` **map**; the `SectionId` **type** alias is at `:15`.
4. `docs/cli.md:9-21` → the Install section is `:9-19`.

### S1 done — landing hero honesty verified end to end

`P11.S1` applied the three plan-specified edits to `web/src/content/landing.ts` (file-header comment,
`vk_9f3c…` auth line with no `live_` tier, and the nested `"source": { "product": "checkout-web" }`
payload) and nothing else. All six validation steps passed: `pnpm typecheck` (0), `pnpm test` (61/61,
unchanged baseline), `pnpm lint` (0), `pnpm format:check` (fails only on 12 pre-existing unrelated files,
`landing.ts` not among them — left alone), `grep -rn "vk_live" web/ src/ docs/` (zero repo-wide matches),
`grep -n "source_product" web/src/content/landing.ts` (exactly the one expected comment-line occurrence).
No doc version was needed: `docs/current/frontend.md:231`'s landing description doesn't assert the false
`vk_live_`/flat-`source_product` shape specifically, so nothing there became stale — no "Doc impact" entry
added for this slice.

### Stale-doc finding for a later slice (not fixed here — `DECOMP` writes no source)

`docs/cli.md:11` ("PyPI publishing is planned (P6)") and `README.md:50` ("PyPI publishing is P6") are
**stale twice over**: `intent.md` records the publish moving from P6 to P11, and operator decision 1
(2026-07-29) then took PyPI off P11's table entirely in favour of `curl | bash`. `docs/current/experience.md:14`
already says "distribution is **P11**". Whichever slice ships the installer (S3) or the skill (S4) should
correct these two install sections to describe the real path; the review consolidates the doc impact.

## Hand-off to P12

- Arm falsifiable **flip probes** for P12's bring-up smoke: `https://vocky.hi2vi.com/install.sh` → **404
  today**, `https://vocky.hi2vi.com/SKILL.md` → **404 today**, and the landing carries the install line.
  All three flip on first deploy. Record them as probes now so P12 proves the flip rather than asserting it.
- The `git+…` channel resolves **GitHub `main`** — the installer is only truthful after an
  operator-gated `git push`. **P12 owns that push** and the clean-environment `curl | bash` end-to-end
  proof.
- The **Cloudflare-not-a-barrier probe is unrunnable in P11**; P12 runs it live.
- P12 **extends `.github/workflows/ci.yml`** with the Postgres-backed pytest job. S4 must shape that file
  so P12 adds a job rather than starting from nothing.
- **Armed flip probe, exact command** (`P11.S3`): `curl -sS -o /dev/null -w '%{http_code}'
  https://vocky.hi2vi.com/install.sh` → **`404` today**; must read **`200`** after the first deploy. Same
  shape for `/SKILL.md` once `P11.S4` lands it.
- **`git push` is a hard prerequisite for the hosted installer to be honest, not a nicety** (`P11.S3`):
  `uv tool install git+https://github.com/leetusik/vocky` resolves whatever is on **GitHub `main`**, which
  is **45 commits behind local** as of this slice (remote head `3e1e85a`, last pushed 2026-07-17) — every
  commit of P9/P10/P11 is unpushed, so installing from the real `git+https://` target today would silently
  deliver a pre-P10 CLI with no org keys and no `vocky capture`. `P11.S3` therefore verified
  `web/public/install.sh` only against a **local** target (`VOCKY_INSTALL_TARGET=$PWD`), never against the
  real GitHub URL. **After pushing, P12 must install-and-check, not assert**: run the installer (or `uv
  tool install --reinstall git+https://github.com/leetusik/vocky`) into a clean environment and assert
  `vocky --version` reads **`0.2.0`** (or newer) and `vocky capture --help` renders — exactly the two
  assertions `P11.S3` already proved against the local target.

## Constraints

### Out of scope for P11 (explicit)

- **No PyPI publish**, no `uv publish`, no version-related PyPI work beyond an optional CLI version bump.
- **No new backend capture contract** — `POST /api/feedback`'s shape is not redesigned.
- **No change to the `source_product` read-path shape** anywhere (web feedback pages,
  `web/src/lib/vocky/types.ts`, `smoke.py`). Only the *capture request* is nested.
- **No deploy, no push, no live verification** — all P12.

### Standing constraints

- `vocky.cli.*` imports stay typer / httpx / stdlib / `vocky.smoke` only (lean-install isolation).
- Copy lives in `web/src/content/`, never inline in components.
- **RESPECT THE DESIGN** at apply time — ship every designed element as designed; never drop, simplify,
  or "improve" one to save effort. This rule goes in each apply slice's `plan.md` **and** its dispatch
  prompt.
- The design slice (`P11.S5`) is **never dispatched to an executor** and **never writes implementation
  code**.

## Open Questions

- **S2**: `--token` vs `VOCKY_API_TOKEN` vs stored precedence, and where (if anywhere) a `vk_` key is
  persisted — it must not be conflated with the session token in `config_store`. Settle at S2 plan time.
- **S4**: the canonical skill's home — a new top-level `skills/<name>/SKILL.md` is the recommendation, but
  the exact path/name is settled at S4 plan time. It must **not** live under `.claude/skills/` or
  `.agents/skills/`.
- **S5**: every visual question is posed back to Claude Design, never answered here.

### S2 done — `VOCKY_API_TOKEN` resolution + `vocky capture` landed

`P11.S2` closed both gaps the phase objective names: `VOCKY_API_TOKEN` now exists (`resolve_api_token()`
in `src/vocky/cli/context.py`) and `vocky capture` is a real top-level command
(`src/vocky/cli/capture.py`, registered in `app.py`). All design decisions in the slice's `plan.md`
(token resolution shape, the `context.make_client(token=..., use_stored_token=False)` seam, the
401-override threading, command shape, registration, the `keys mint` hint, the version bump) were
implemented as specified — nothing was re-litigated.

**Exact surface `P11.S4`'s end-user skill should author against:**

- **Env var**: `VOCKY_API_TOKEN` — the only way to supply the `vk_` key; no `--token` flag exists. Missing
  or blank → exit non-zero, no HTTP call, stderr is exactly:
  `VOCKY_API_TOKEN is not set — mint a key with \`vocky keys mint\` and export it.`
- **Command**: `vocky capture MESSAGE --product PRODUCT [--integration I] [--value 1|2] [--comment C]
  [--tag T ...] [--session-id S] [--user-id U] [--project P]`. `MESSAGE` positional; pass `-` to read the
  whole message from stdin instead of fighting shell quoting. `--product` is the only required option.
  `--tag` is repeatable; omitted entirely from the request body when not given (never sent as `[]`).
  `--project` is REST-only-parity: honored only for an **org-level** `vk_` key, ignored by a project-bound
  one (same as the REST/MCP contract already documented).
- **Success output** (exact string, request id printed in full): `Captured — request_id <full id>`.
- **401 output** (exact string; deliberately not "run `vocky login`" — that message is reserved for the
  session-token commands): `Unauthorized — check VOCKY_API_TOKEN (the key may be wrong or revoked).`
- **Auth**: `Authorization: Bearer <vk_ key>` — never the stored session token. Built via
  `context.make_client(token=api_token, use_stored_token=False)`, which structurally guarantees the two
  credentials can't cross.
- **Two-export quickstart** (now real): `export VOCKY_BASE_URL=...` + `export VOCKY_API_TOKEN=vk_...` +
  `vocky capture "..." --product ...`. `vocky keys mint`'s output now includes a hint line pointing at this
  exact export, right before the show-once key line.
- **Version**: `pyproject.toml` is now `0.2.0` (was stale `0.1.0` since before P10). `vocky --version` only
  reflects it after a reinstall (`importlib.metadata` reads installed metadata, not the source tree) — the
  installer (`P11.S3`) reinstalls on every run, so this is a non-issue there.
- **Import isolation held**: `vocky.cli.*` (including new `capture.py`) still imports only typer / httpx /
  stdlib / `vocky.smoke`. The lean install from a built wheel resolves exactly **15 packages** (httpx +
  typer + transitives, no pydantic/sqlalchemy/uvicorn/psycopg) — verified with `uv build` +
  `uvx --from dist/vocky-0.2.0-py3-none-any.whl vocky --version`.
- **Not proven**: no live server round trip — every test stubs the transport. The real end-to-end proof
  (a running server, a real `vk_` key, a real 202) is P12's live smoke per the phase's hand-off section.

**Environment finding for later full-suite baselines**: this dev environment has a live Postgres reachable
on the test suite's default `127.0.0.1:55432`, so `uv run pytest -q` here shows **0** errors, not the
~108 `psycopg.OperationalError`s the phase's earlier citations (from `P6.S9`) describe for a no-DB
environment. Establish pre/post-slice baselines by comparison (e.g. `git stash` the slice's diff and
re-run) rather than assuming the ~108 number will reproduce here.

**Docs correction beyond the plan's three bullets**: `docs/cli.md`'s end-to-end walkthrough step 4
("Capture is not a CLI command in this release") was left false by the plan's specified edits alone, so it
was corrected too (now shows both `vocky capture` and the raw-HTTP equivalent) — a minimal, same-file
consistency fix, not a scope expansion.

### S3 done — `web/public/install.sh` landed and verified against a local target

`P11.S3` shipped the `curl | bash` installer at `web/public/install.sh` (61 lines) exactly to the plan's
shape: `set -euo pipefail`, two constants (`UV_BIN_DIR`, `INSTALL_TARGET` with the `VOCKY_INSTALL_TARGET`
override), `say`/`die` helpers, **every executable statement inside `main()`**, and **`main "$@"` as the
literal last line**. All eight validation steps passed — see `result.md` for verbatim output. Two findings
worth recording for later slices:

- **The `main()` wrapper's safety held under both truncation shapes tested**: piping a mid-function
  prefix (`head -n 40`) produced a bash **parse error** (exit 2, no output, `main` never reached — a
  truncated function body can't even finish parsing); piping the file up through the closing `}` but
  before the final `main "$@"` line (`head -n 59`) parsed clean and exited **0 with no output** (the
  function is defined but never called). Either cut point proves the same thing: a truncated `curl | bash`
  can never half-execute.
- **The `uv` bootstrap branch WAS exercised**, not skipped: validation used `env -i` with a minimal PATH
  (`/usr/bin:/bin:/usr/sbin:/sbin`), which has no `uv` on it regardless of the host machine's own `uv`
  install, so both the fresh-install run and the second (idempotency) run against the same temp `HOME`
  installed `uv` via the Astral installer inside the script. This is stronger evidence than the plan
  anticipated (it expected the branch might be skipped in an environment with `uv` already on PATH).

**Exact final install line — `P11.S4`'s skill and the `P11.S5` design handoff both quote this verbatim**:

```
curl -fsSL https://vocky.hi2vi.com/install.sh | bash
```

Both `docs/cli.md` and `README.md` now show this exact line, explicitly marked "once the site is live",
with the checkout-based install kept as what works today, and no PyPI promise anywhere in either file
(verified: `grep -rn "PyPI\|pip install vocky\|uv publish" README.md docs/cli.md` — zero matches).

**Not proven** (must not be asserted as done): no live `https://vocky.hi2vi.com/install.sh` fetch — the
site is not deployed; the `404 → 200` flip is P12's; and the real `git+https://github.com/leetusik/vocky`
target was **never installed from** in this slice — GitHub `main` is 45 commits behind local (see "Hand-off
to P12" above), so installing from it today would silently deliver a pre-P10 CLI. `VOCKY_INSTALL_TARGET`
stood in for it throughout validation.

Untouched, as the plan required: `web/Dockerfile`, `web/next.config.ts`, `deploy/vocky.conf` — all three
already serve `web/public/` correctly (confirmed again this slice: no dockerignore/gitignore excludes
`install.sh` or `public/`, `Dockerfile:40` still copies `public/`).

## Doc impact

- **S2** (`P11.S2`): `vocky capture` + `VOCKY_API_TOKEN` are now real — `docs/current/experience.md`
  (agent-facing capture/onboarding guidance should mention the CLI path alongside REST/MCP) and
  `docs/current/operations.md` (CLI import-isolation section, if it enumerates command modules, should
  list `capture.py`) may need updates at the phase review; `docs/current/api.md` is unaffected (no backend
  contract changed).
- **S3** (`P11.S3`): install now has a real path — `docs/current/operations.md` (its CLI/install narrative,
  if any, should mention `web/public/install.sh` and the `curl -fsSL https://vocky.hi2vi.com/install.sh |
  bash` line, marked as live only once the site deploys) and `docs/current/experience.md` (onboarding
  guidance's "how do I get the CLI" gap is now closed) both describe the install story and may need updates
  at the phase review. Source files edited directly (not doc versions): `docs/cli.md:9-19` and
  `README.md:48-63`, both corrected to drop the stale "PyPI planned (P6)" framing and describe the hosted
  `curl \| bash` line (marked "once the site is live") plus the checkout path as what works today, with the
  lean/`server`-extra split stated as packaging fact, no PyPI promise.
