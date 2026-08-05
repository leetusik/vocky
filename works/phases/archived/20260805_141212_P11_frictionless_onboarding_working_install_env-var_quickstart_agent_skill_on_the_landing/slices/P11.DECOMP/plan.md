# P11.DECOMP — plan

## Context

`P11` (*Frictionless onboarding: working install, env-var quickstart, agent skill on the landing*) is
`planned`; only `P11.DECOMP` and `P11.REVIEW` exist. This slice cuts the phase into middle slices and
seeds `phase.md`.

The phase exists because vocky's onboarding story is currently **not real**:

- The `vocky` CLI **cannot be installed** except from a checkout (`docs/cli.md:9-21`, `README.md:48-63`).
- **`VOCKY_API_TOKEN` does not exist anywhere** in the tree — grep over `src/vocky/**` finds exactly five
  env reads (`cli/context.py:76` `VOCKY_BASE_URL`, `cli/config_store.py:32,36`, `smoke.py:20,187`). The CLI
  is session-token-only and **has no capture command at all**, so a `vk_` key has no CLI consumer.
- There is **no end-user skill**. All 16 `.claude/skills/*` and 15 `.agents/skills/*` are repo-workflow
  machinery; none mentions capturing feedback.
- The hero publishes **two falsehoods** in `web/src/content/landing.ts`: `:57` `Bearer vk_live_9f3c…`
  (no such tier exists — `src/vocky/app_api.py:241,320` mint `"vk_" + opaque`), and `:59`
  `"source_product": "checkout-web"` at top level, while capture **requires** nested
  `source: {product}` (`src/vocky/capture.py:27-31,37,274`). The rationale comment at `landing.ts:11-13`
  asserts the wrong shape too.

**This is a design-bearing phase**, so it decomposes in **two passes** (`design-cowork`): this `DECOMP`
creates only the groundwork slices, the design slice, and `P11.DECOMP2`, and records a **build
inventory** in `phase.md` instead of build slices.

### Operator decisions (2026-07-29) — build around these, do not relitigate

1. **Install = `curl | bash`, not PyPI.** Ship `web/public/install.sh`. **No `uv publish` in P11**; the
   P6.S9 publish hand-off stays unexercised and `dist/`'s `0.1.0` artifacts stay stale.
2. **Add `vocky capture`.** `VOCKY_API_TOKEN` gets a first-class CLI consumer — a new capture command
   POSTing to `/api/feedback` with the `vk_` key.
3. **CI gate = a new minimal `.github/workflows/ci.yml`** on push + pull_request (parity script + web
   lint/typecheck/vitest). P12 later extends that same file with the Postgres pytest job.

### The honesty problem the curl choice creates — and why it is resolved

A hero line naming `https://vocky.hi2vi.com/install.sh` 404s today. It is **not** a live falsehood,
because **the site itself is not deployed** (`docs/current/experience.md:14`; the only workflow,
`deploy-production.yml`, is `workflow_dispatch`-only and has never run). The landing page and
`install.sh` therefore go live **in the same P12 bring-up**, so no live landing ever serves a dead
command. `DECOMP` must record this as an explicit hand-off to P12 with armed flip probes, and every
P11 `result.md` must say plainly what was *not* behaviorally proven.

## Grounded facts DECOMP must seed into `phase.md`

Verify each before recording it; flag any disagreement in `phase.md` rather than silently deviating.

**Capture contract** (`src/vocky/capture.py`, `src/vocky/api.py`, `src/vocky/auth.py`)
- `POST /api/feedback` requires `message` and nested `source: {product, integration?}`;
  `source.product` must be non-blank (`capture.py:274`). REST-only extras `attachment_ids` and
  `project` (org-key destination, default `"default"`, `capture.py:80-81,325-368`). Response
  **202** `{request_id, accepted_at, status:"accepted"}` (`capture.py:84-89`).
- Auth is **`Authorization: Bearer vk_…`**, not `X-API-Key` (`auth.py:66-81,144-215`). The same
  middleware guards `/api/*` **and** `/mcp` (`auth.py:171-174`), so a `vk_` key drives both; the single
  MCP tool is `capture_feedback` (`src/vocky/tools/capture_feedback.py:36-37`).
- **`vk_` is never validated as a prefix** — auth resolves purely by `sha256_hex` (`auth.py:130-133`).
- A `vk_` key authorizes **only** `/api/*` + `/mcp`. Every existing CLI command talks to `/app/*` with a
  **session** token — which is exactly why `VOCKY_API_TOKEN` needs `capture` to have any consumer.

**CLI** (`src/vocky/cli/`)
- `context.py:66-84` base-URL precedence `--base-url` > `VOCKY_BASE_URL` > stored > `http://127.0.0.1:8000`;
  `authed_client()` (`:61-62`) hard-fails "Not signed in". `client.py:103-106` already injects
  `Authorization: Bearer`, so a `vk_` path **reuses `ApiClient` unchanged**.
- `config_store.py:25-40,66-91` — `VOCKY_CONFIG_DIR` > `$XDG_CONFIG_HOME/vocky` > `~/.config/vocky`,
  dir `0700` / file `0600`, keys `token` + `base_url` only.
- **Import isolation is load-bearing** (`docs/current/operations.md:124`): `vocky.cli.*` may import only
  typer / httpx / stdlib / the httpx-only `vocky.smoke`. A server-side import silently breaks the lean
  install. Guard: `uvx --from dist/*.whl vocky --version`.
- No linter/formatter is configured for Python.

**Web / serving** (all verified)
- `web/public/` exists but holds only `.gitkeep`. `web/next.config.ts:55` `output: "standalone"`;
  `web/Dockerfile:40` `COPY --from=build /app/public ./public`; `deploy/vocky.conf:282-288` is a bare
  `location / { proxy_pass … :3000; }` with no more-specific location shadowing a root path.
  → `web/public/install.sh` and `web/public/SKILL.md` serve at `/install.sh` and `/SKILL.md` with
  **zero infra work**. Caveat: `X-Content-Type-Options: nosniff` is global (`next.config.ts:43`), so a
  browser will *download* `.md` rather than render it — fine for `<a download>`, and a route handler
  would be needed only for in-browser viewing.
- Landing composition: `web/src/app/page.tsx:32-46` → `LandingNav`, `Hero`, `TrustStrip`, `HowItWorks`,
  `Showcase`, `Features`, `Pricing`, `ClosingCTA`, `LandingFooter`. Hero snippet assembled at
  `hero.tsx:27-30` from `LANDING.hero.request`; right column is `EndpointCard` (`hero.tsx:72-74`).
- **Copy-as-data is a house rule** — components hold no literal copy; everything lives in
  `web/src/content/`. Section anchors are typed `SectionId` (`web/src/content/section-ids.ts:8-13`),
  so a new section **must** add its id there.
- Existing primitives to reuse, not rebuild: `ui/endpoint-card.tsx` (`<pre>` in a forest panel),
  `show-once-key.tsx:43` (a working `navigator.clipboard.writeText` + failure fallback — the copy
  mechanics to extract), `ui/reveal.tsx`, `ui/section.tsx` CVA tones.
- **`source_product` is correct on the read path** — `web/src/app/(app)/feedback/*`,
  `web/src/lib/vocky/types.ts:231,329`, and `src/vocky/smoke.py:141` (a query filter). **Only the capture
  request is nested.** Do not "fix" those.
- Tests: vitest, `environment: "node"`, `include: ["tests/**/*.test.ts"]` (`web/vitest.config.ts:30-33`);
  5 files, 61 tests, **none asserts a copy constant**. No jsdom/RTL — so testable logic must be extracted
  into pure helpers. `web/.dockerignore` excludes `tests`, so a parity gate runs in CI, never in the image.

**Design** — round 01 (`docs/reference/design/rounds/01-brand-app-landing/`) designed the brand + landing;
`SIGNOFF.md` records design project **`1eaa0803-46e3-426a-ab04-17a802170234`** (target by **id**), 30
cards, token delta applied by P9. Tokens live in `web/src/app/globals.css`; the applied system is
documented at `docs/current/frontend.md:84-87,229-231,269-270`. The next round is **02**.

**The `git+` shipping caveat (knowledge lost real time to this).** `uv tool install
git+https://github.com/leetusik/vocky` installs whatever is on **GitHub `main`**, so P11's `vocky
capture` is unreachable to installer users until an operator-gated `git push`. The workspace never
pushes unasked. → P11 verifies the installer against a **local** target in an isolated temp `HOME`, and
hands the real push + live proof to P12.

**Three env-var blockers knowledge documented — all apply, all belong in the design handoff:**
1. A repo `.env` is **never** auto-loaded by Claude Code or Codex, and a secret in a repo file risks an
   accidental commit → recommend `~/.zshenv`.
2. Codex's `workspace-write` sandbox **denies outbound network by default** → `[sandbox_workspace_write]
   network_access = true` in `~/.codex/config.toml`. Claude Code needs nothing.
3. Cloudflare was empirically **not** a barrier for knowledge — but vocky's site is not live, so the probe
   **cannot run in P11**. Record it as a P12 check; do not design around an unverified blocker.

## The decomposition to create

Six slices. `DECOMP` creates **bare folders only** — never pre-fills any `plan.md`.

| Slice | Order | Kind | Risk | Depends on | Name |
|---|---|---|---|---|---|
| `P11.S1` | 1 | implementation | **low** | — | Landing hero honesty: nested `source.product` + real `vk_` key shape |
| `P11.S2` | 2 | implementation | **medium** | — | CLI: `VOCKY_API_TOKEN` resolution + `vocky capture` over `/api/feedback` |
| `P11.S3` | 3 | implementation | **medium** | — | `curl \| bash` installer: `web/public/install.sh` |
| `P11.S4` | 4 | implementation | **medium** | `P11.S2` | Canonical end-user `SKILL.md`, served byte-copy, parity script + first CI workflow |
| `P11.S5` | 5 | **co-work** | **high** | `P11.S4` | Design round 02: hero install row, agent env-var quickstart, skill-on-landing |
| `P11.DECOMP2` | 6 | decomposition | **high** | `P11.S5` | Decompose the build from the landed design |

```sh
python3 scripts/workflow.py new-slice --phase P11 --slice P11.S1 \
  --name "Landing hero honesty: nested source.product + real vk_ key shape" \
  --kind implementation --risk low --order 1
python3 scripts/workflow.py new-slice --phase P11 --slice P11.S2 \
  --name "CLI: VOCKY_API_TOKEN resolution + vocky capture over /api/feedback" \
  --kind implementation --risk medium --order 2
python3 scripts/workflow.py new-slice --phase P11 --slice P11.S3 \
  --name "curl | bash installer: web/public/install.sh" \
  --kind implementation --risk medium --order 3
python3 scripts/workflow.py new-slice --phase P11 --slice P11.S4 \
  --name "Canonical end-user SKILL.md, served byte-copy, parity script + first CI workflow" \
  --kind implementation --risk medium --order 4 --depends-on P11.S2
python3 scripts/workflow.py new-slice --phase P11 --slice P11.S5 \
  --name "Design round 02: hero install row, agent env-var quickstart, skill-on-landing" \
  --kind co-work --risk high --order 5 --depends-on P11.S4
python3 scripts/workflow.py new-slice --phase P11 --slice P11.DECOMP2 \
  --name "Decompose the build from the landed design" \
  --kind decomposition --risk high --order 6 --depends-on P11.S5
```

If `--kind co-work` is rejected by `scripts/workflow.py`, **stop and report** — do not substitute a
different kind; the co-work kind is what keeps the design slice off the executor dispatch path.

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
- **S5 `high`** — `design-cowork` forbids ever rating a design slice `low`. Never dispatched.

## Slice intents to record in `phase.md`

Record these as intents for the orchestrator to plan at each slice's turn. **Do not pre-fill any
`plan.md`.**

- **S1 — Hero honesty.** In `web/src/content/landing.ts`: `:57` `vk_live_9f3c…` → a `vk_`-shaped stub
  matching `"vk_" + secrets.token_urlsafe(32)`; `:58-64` top-level `"source_product": "checkout-web"` →
  nested `"source": { "product": "checkout-web" }`; and correct the false rationale comment at `:11-13`.
  No component edit — `hero.tsx` is untouched. **Copy inside an already-designed component is not a
  design round** (the line knowledge drew crisply). Verify with `pnpm typecheck && pnpm test`.
- **S2 — CLI capture.** `VOCKY_API_TOKEN` in `cli/context.py` beside `VOCKY_BASE_URL`, and a new
  `cli/capture.py` registered in `app.py`. Precedence to settle at plan time (`--token` > env > stored?);
  the key is a `vk_` credential, **never** the session token, and the two must not be conflated in the
  config store. Build the nested `source` correctly; surface the 202 `request_id`; map `401` to "check
  `VOCKY_API_TOKEN`" (not "run `vocky login`"). **Keep imports lean** — typer/httpx/stdlib only. Consider
  a version bump off the stale `0.1.0` (`pyproject.toml:6-7`), since the installer prints
  `vocky --version`. Terse tests only.
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
- **S5 — Design round 02 (`co-work`).** Orchestrator-run **inline on the main thread**; never dispatched
  (no executor has `DesignSync`). Writes `docs/reference/design/rounds/02-onboarding/handoff.md` only —
  **zero implementation code** — then `pending`, then read-back, land as-is, SIGNOFF. Target the design
  project **by id** `1eaa0803-46e3-426a-ab04-17a802170234`. The handoff must require **one card per
  reviewable unit** with the line-1 `@dsCard` marker, plus `result.md` and `build-prompt.md`; carry the
  three env-var blockers above as content to surface; state round 01's brand as **locked**; and **pose
  every open question back** rather than answering it.
- **`P11.DECOMP2`** — cuts the build slices from the landed design and `build-prompt.md`, at orders after
  its own: backing work first, the design implementation after, then any fidelity fix.

## Build inventory to record in `phase.md` (what to build, not how)

This is what the S5 handoff's scope checklist is written from. The design is free to add to it and cut
from it.

1. **Hero install command row** — the `curl | bash` line, copyable, in the hero's left column.
2. **Agent quickstart section** — the two-env-var contract (`VOCKY_BASE_URL` + `VOCKY_API_TOKEN`) as the
   recommended agent path: the `~/.zshenv` block, the Codex `network_access` trap, and a verify/health
   snippet with success and failure legends.
3. **Skill-on-landing section** — a preview pane over the served `/SKILL.md` (build-time `fs` read of the
   **served** copy, so the preview can never fork from the gated artifact), **Copy the skill** (fetching
   the served file rather than embedding a fork), and **Download** as a plain `<a href="/SKILL.md" download>`.
4. Consequent **nav / `SectionId` additions** (`web/src/content/section-ids.ts`) and any `LandingNav` entry.

Also record, as apply-time notes for DECOMP2's slices: copy payloads should be **byte-locked constants
with display deliberately separate from clipboard bytes**, guarded by a vitest that re-spells them —
vocky has no such test today, and it would be the first.

## Hand-off to P12 (record in `phase.md`)

- Arm falsifiable **flip probes** for P12's bring-up smoke: `/install.sh` → 404 today, `/SKILL.md` → 404
  today, and the landing carries the install line. All three flip on first deploy.
- The `git+…` channel resolves **GitHub `main`** — the installer is only truthful after an
  operator-gated `git push`. P12 owns that push and the clean-environment `curl | bash` end-to-end proof.
- The Cloudflare-not-a-barrier probe is **unrunnable in P11**; P12 runs it live.
- P12 extends `ci.yml` with the Postgres-backed pytest job.

## Out of scope (state explicitly)

- **No PyPI publish**, no `uv publish`, no version-related PyPI work beyond an optional CLI version bump.
- **No new backend capture contract** — `POST /api/feedback`'s shape is not redesigned.
- No change to the `source_product` read-path shape anywhere.
- No deploy, no push, no live verification — all P12.

## Validation

1. `python3 scripts/workflow.py validate` → passes.
2. `python3 scripts/workflow.py next` → reports `P11.S1` as the next slice.
3. `works/backlog.md` lists all six new slices with the intended kinds, risks, and orders.
4. Every new slice folder contains **only** `slice.json` — no `plan.md`, no `result.md`.
5. `phase.md` carries: the operator decisions, the grounded facts, the slice table with rationale, the
   slice intents, the build inventory, the P12 hand-off, and an empty **`## Doc impact`** heading for
   later slices to append to.
6. **No source file is modified** — decomposition writes only `works/` state and `phase.md`.
