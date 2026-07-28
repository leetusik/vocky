# Intent — P11

- Captured at: 2026-07-28T16:05:17+09:00
- Origin: operator

## Original Input (verbatim)

_One `/create-phase` run created P10, P11 and P12 from this single request; the full original is preserved in each.
**P11 owns the "how to user to install etc.." half** of the clarified answer._

> and revise phases. reference how ../knolwedge did. We'll follow them.

Follow-up (same session, answering the clarifying questions):

> 1. I meant learn how it implemented and we'll follow that in general. like org/project, key, like stuff. how to
> user to install etc..

> don't need to change anything. about it. while you asking this question. i /update-workspace already.

## Confirmed Intent (refined + clarified)

Learn from how `../knowledge` **implemented** its onboarding (its P20, "Frictionless onboarding: hero, install,
env-var quickstart, skill on landing") and follow that in vocky. Make the path from "sees the landing page" to "an
agent is capturing feedback" real end to end:

- **A working install line on the landing page.** Vocky's `vocky` CLI is **not installable today** — it is not on
  PyPI, and `docs/cli.md:11-17` / `README.md:46-61` tell users to install from a checkout. The landing page doesn't
  mention the CLI at all, so nothing is currently *falsified* — but equally there is nowhere to put an install
  command without it becoming a lie the moment it is written. Two viable paths, not mutually exclusive; DECOMP picks:
  - **PyPI** — `P6.S9` already built the wheel and sdist (`dist/vocky-0.1.0-*`, lean CLI = `httpx` + `typer` only,
    heavy deps behind a `server` extra) and verified `uvx --from dist/…whl vocky --version`. It needs exactly one
    operator action: `uv publish` with a PyPI token. Then `uv tool install vocky` on the hero is true.
  - **A `curl | bash` installer** — what knowledge actually chose, at zero infra cost.
- **The env-var quickstart, as the recommended agent path.** Today there is **no environment-variable path for a
  credential at all**: `VOCKY_BASE_URL` and `VOCKY_CONFIG_DIR` exist (`src/vocky/cli/context.py:66-84`,
  `src/vocky/cli/config_store.py:32`), but `VOCKY_API_TOKEN` does not exist anywhere, there is no `--token` flag,
  and the CLI is session-token-only with no capture command (`docs/cli.md:175`). Knowledge shipped exactly two vars
  (`KB_API_BASE_URL` / `KB_API_TOKEN`) as "the whole contract" because two exports give every coding agent on the
  machine equal access with no plugin install anywhere. Vocky needs the same, and the missing `VOCKY_API_TOKEN` is
  the single biggest gap in the story.
- **An end-user agent skill, published on the landing page.** Vocky has **no end-user skill today** — all 16
  `SKILL.md` files under `.claude/skills/` are repo-development workflow skills (phase/slice management), none of
  which mention capturing feedback, `vk_` keys, or vocky's product API. So P11 must *author* one (capture feedback
  over REST and/or the `/mcp` mount), then publish it the way knowledge did: a real file served statically, copyable
  and downloadable, behind a **byte-parity CI gate** so the landing artifact can never fork from the canonical.
- **Honesty fixes to the existing landing copy.** Two are outright wrong today:
  - The hero shows a top-level `"source_product": "checkout-web"`, but the capture schema requires a **nested**
    `source.product` (`src/vocky/capture.py:25-29`, normalization at `:266`) — copy-pasting the hero body yields a
    validation error.
  - The hero shows `vk_live_9f3c…`, implying an environment-tiered key format **that does not exist**; real keys are
    `vk_` + `secrets.token_urlsafe(32)` (`src/vocky/app_api.py:234`).
  - Related, and why this phase follows P10: the depicted "create a project, mint a key" step is manual dashboard
    work today because signup provisions no project. P10 fixes the flow; P11 depicts it truthfully.

**Scope fence**: any **net-new landing section** goes through a `design-cowork` gate (Claude Design + operator make
the visual decisions; the design slice writes no implementation code and is never dispatched to an executor).
Changing copy *inside* an already-designed component is **not** a design round — knowledge drew that line crisply
and repeatedly. No new backend capture contract: the `POST /api/feedback` shape is not redesigned here.

## Clarifications Resolved

- Q: "Revise phases" — do you mean adopt knowledge's phase-*authoring* conventions, mirror its *roadmap*, both, or
  rescope the in-flight P6? — A (verbatim): "1. I meant learn how it implemented and we'll follow that in general.
  like org/project, key, like stuff. how to user to install etc.." → **the implementation substance**, not the
  workflow conventions. P11 takes the install/onboarding half.
- Q: Which new phases should I create now? — A: Accounts v2, Frictionless onboarding, Post-launch hardening.
  **Public/shareable feedback (knowledge's P19 analogue) was offered and deliberately not selected** — it is not
  planned.
- Q: Where should the adopted phase-authoring conventions be recorded? — A (verbatim): "don't need to change
  anything. about it. while you asking this question. i /update-workspace already." → **no change to `CLAUDE.md` /
  `AGENTS.md` or any workflow machinery.**

## Notes

- **Sibling phases from the same request**: P10 (accounts v2 — org/project/key model) and P12 (post-launch
  hardening). Execution order **P10 → P11 → P12**. P11 **depends on P10**: the copy depicts the org /
  default-project / key flow P10 finalizes, and writing marketing copy against a model that is about to change is
  how the current hero got its two untrue lines. Mirrors knowledge's own P18 → P20 argument.
- **P11 also depends on the `P6.S9` publish decision.** If the operator runs `uv publish`, PyPI is the hero's
  install line and this phase gets simpler. If not, the installer path is the fallback. Do not plan the install
  slice before that is settled.
- **The site is not live while this phase runs.** Per the operator (verbatim: _"mind that deploy will be done at p12
  so p6 doesn't have to mind it"_), the production bring-up moved out of P6 into **P12**, which runs *after* this
  phase. Two consequences DECOMP must plan around:
  - **Nothing here can be verified against a real origin.** A `curl | bash` installer served from `web/public/`, the
    `/SKILL.md` static route, and any absolute-URL copy can only be checked locally (`next build` + the standalone
    server) — the live 404→200 flip that knowledge used as its proof lands in P12's bring-up smoke. Plan the
    verification accordingly and say plainly in `result.md` what was *not* behaviorally proven.
  - **A `curl | bash` install line naming `https://vocky.hi2vi.com` is untrue until P12 deploys.** If that path is
    chosen over PyPI, either the copy ships behind the launch or the hero states a PyPI line that is true the
    moment `uv publish` runs. Do not ship a hero command that 404s — that is exactly the class of defect this phase
    exists to remove.
- **Reference material in `../knowledge`, worth reading at DECOMP time** (read-only; never edit that repo):
  - `works/phases/active/P20/phase.md` — the whole phase, including the operator-approved fixed decisions
  - `web/public/install.sh` (50 lines) — all logic inside `main()` with `main "$@"` as the last line, **so a
    partially-downloaded `curl | bash` can never execute a half-written script**; bootstraps `uv` if missing;
    `uv tool install --reinstall` so re-runs are idempotent and upgrade-safe; no sudo, nothing system-wide; ends by
    printing the next command. Serving it costs **zero infra** — `output: "standalone"` + `COPY public ./public` in
    the Dockerfile + the nginx `/` catch-all already serve `web/public/*`, and `curl | bash` is
    content-type-agnostic, so no route or MIME work. Vocky's `web/Dockerfile` and `deploy/vocky.conf` (P6.S4/S6)
    have the same shape.
  - `scripts/skills_parity.py` — the CI byte-parity gate that holds the served landing copy of the skill to a
    **full-file byte match** against the canonical, so it can never fork
  - `web/src/components/marketing/{feature-skill,skill-pane,copy-button,snippet-block}.tsx` — Download is a plain
    `<a href="/SKILL.md" download>`; Copy **fetches the served file** rather than embedding a pasted fork; the
    preview pane does a build-time `fs.readFileSync` of the *served* file
  - `web/src/content/marketing/content.ts` — the env-var copy payloads are **byte-locked constants** with a vitest
    guarding them, and the display form deliberately differs from the copy payload
- **Three real blockers knowledge documented for the env-var path — all apply to vocky:**
  1. **A repo `.env` is never auto-loaded** by Claude Code or Codex, so a resolver would never see it — and a secret
     in a repo file risks an accidental commit. Recommend `~/.zshenv`: sourced by every zsh invocation, so every
     Bash call, every Codex exec and every repo inherits it, and the key stays out of all repos.
  2. **Codex's `workspace-write` sandbox denies outbound network by default** — the POST fails and the skill
     silently degrades. Fix is `[sandbox_workspace_write] network_access = true` in `~/.codex/config.toml`. Claude
     Code needs nothing.
  3. **Cloudflare was empirically *not* a barrier** — knowledge disproved its own assumed blocker with a live probe
     rather than reasoning about it. Do the same before designing around it.
- **The shipping caveat that cost knowledge real time**: `git+…#subdirectory=cli` installs whatever is on GitHub
  `main`, so CLI changes were unreachable by installer users until an operator-gated `git push`. They proved the
  flip empirically (pre-push install resolved to the old commit and lacked the new line; post-push had it) rather
  than asserting it. Any vocky install path has the same class of "what does the user actually get" question —
  verify by installing into a clean environment, don't assert.
- **Knowledge's "honesty over features" precedent**: the operator asked for a password generator; fact-finding
  showed the flow already worked and the hero simply never depicted the password prompt, so the fix was to *show the
  prompt*. Prefer the same posture here — depict what is true before building anything new.
- Live cosmetic gotcha knowledge hit after its own accounts phase: once signup pre-creates the default project, a
  brand-new account's first `init` reports the project as *already existing*, not *created* — so a hero mockup
  showing "(created)" is only honest for a genuinely fresh org.
