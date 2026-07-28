# Intent — P1

- Captured at: 2026-07-15T14:55:53+09:00
- Origin: operator

## Original Input (verbatim)

> 1. change license to full opensource. maybe MIT
> 2. gonna start full SaaS but no paid plan.
>  - tenant, project, and usage, monitoring feature
>  - not only feedback write and stuff but get and all other api endpoint required. to provide other service admin pannel(operator page) can access feedback stuff directly(like changple5 projects)
>  - current token based login remove, make it legitmate account feature
>  - support proper search engine for feedbacks, across the project for a user
>  - we need tenant dashboard and project detail pages
>  - let's say you are my user, make the user able to sign up and do neccessary cred setting via claude code or codex. not by it's plugin I guess but make cli feature to login, and do sutff, and gives proper help docs or guide docs so that a user don't even to visit our website but use the vocky feature.
>  - for now, focus on restapi that only triggered by real human not ai agents feedbacks(this for later, drop exsiting feature for now)
>  - but we are going to make it's landing page and proper webpage btw. claude design gate and stuff. reference the hi2vi_web dir in this host.
>  - the domain will be use vocky.hi2vi.com. knowledge already using knowledge.hi2vi.com btw. we will use `ssh oracle-cloud` box for production, and `edge` for nginx conf setup.

## Confirmed Intent (refined + clarified)

Part of the vocky SaaS pivot confirmed on 2026-07-15, split across phases P1–P6 (this shared original request appears verbatim in each phase's intent.md; each phase records its own confirmed scope).

This phase (P1) covers the relicense and the de-scope:

- Change the license from AGPL-3.0 to MIT (full open source), updating LICENSE and any license references (README, pyproject, docs).
- Drop the existing MCP / AI-agent-decided feedback capture feature for now (to be revisited later): remove the MCP server wiring, tools, config, and related docs entirely — git history keeps it recoverable.
- Refocus the product surface and docs on REST API feedback triggered by real humans, as the base for the SaaS pivot in P2–P6.

## Clarifications Resolved

- Q: One phase or several — how should the work be split? — A: Six phases: P1 relicense + agent-capture retirement; P2 accounts/tenancy/projects core; P3 feedback API v2 + search + usage monitoring; P4 web app (tenant dashboard + project detail pages); P5 CLI + agent-first onboarding; P6 landing page + production deploy.
- Q: How to handle the placeholder P1 "Bootstrap Intake" (no delete/rename command; unarchivable without a passing review)? — A: Repurpose P1's folder as this first phase.
- Q: How deep should the MCP/agent-capture removal go? — A: Remove the code and surface entirely (not feature-flagged off); git history keeps it recoverable.
- Q: Web stack for the new user-facing surfaces? — A: One new Next.js app in the style of hi2vi_web with the Claude design-gate workflow; the packaged same-origin operator admin UI retires (affects P4/P6, recorded here for shared context).

## Notes

- Deliberately left to each phase's DECOMP: auth mechanism details (email/password vs OAuth, CLI device-flow), search engine choice (Postgres FTS vs external engine), and how per-project API credentials coexist with account auth.
