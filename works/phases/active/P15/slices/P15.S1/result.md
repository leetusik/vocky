# Result — P15.S1: Knowledge — the product and its user-facing surfaces

**Status: done.** The first explainer of the new-maintainer series is published to the personal KB.

## What was produced

One `/explain` run (topic mode, no `here` flag, executed inline by the orchestrator per the phase execution rule):

- **Title:** "Vocky: What It Is and How It Is Used"
- **KB location:** `vocky/2026-08-06-vocky-what-it-is-and-how-it-is-used.html`, document id 25, **v1**
- **URL:** https://knowledge.hi2vi.com/documents/25
- **Save state:** `201`, committed (`9cf1a5e…`), `push_pending: true` (normal — background push)
- **Research section:** skipped-by-judgment — a repo-private product overview has no meaningful external best-practice comparison surface; the document has Background / Intuition / Code / Quiz.

## Coverage

Grounded in `docs/current/product.md` (v0012), `experience.md` (v0013), `frontend.md` (v0009), `docs/cli.md` (headings + walkthrough), `skills/vocky-feedback/SKILL.md`, `web/public/install.sh`, and the `web/src/` + `src/vocky/cli/` structure. Covers: problem/users/non-goals; user → org → project (incl. the org/tenant naming trap); the two-credential mental model (session token vs `vk_` key, project vs org scope, `project_id` null discriminator, keys-are-not-capture-only); the six surfaces as roles with an SVG surface map; async capture with a toy Korean example; `recorded_by` provenance rules; the field taxonomy by responsibility; the three pure clients (web app + BFF/sealed cookie, CLI + credential-plane split, agent skill + two-env-var contract + installer safety shape); 5-question quiz.

## Notes for later slices

- `product.md` and `experience.md` both contain **internally contradictory live-status text** (stale "vocky.hi2vi.com does not answer / is not live" passages alongside the updated "live since 2026-08-04, P12" text). Recorded in `phase.md` — relevant to the REVIEW slice as potential doc-impact and to S5 as corroborating context (the README staleness has the same root cause).
