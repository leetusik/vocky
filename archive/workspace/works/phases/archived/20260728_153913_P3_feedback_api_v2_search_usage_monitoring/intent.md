# Intent — P3

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

This phase (P3) covers the full API, search, and usage monitoring:

- Expose not only feedback write (capture) but get/list and all other required REST endpoints, tenant/project-scoped, so an external service's own admin panel / operator page (like the operator's changple5 projects) can access feedback directly — vocky's UI is no longer the only review surface.
- Support a proper search engine for feedbacks, across all of a user's projects (not just per-project filtering).
- Add usage monitoring per tenant/project (capture volume, API usage, and similar operational metrics).
- The API remains focused on feedback triggered by real humans (the agent-capture path was dropped in P1).

## Clarifications Resolved

- Q: One phase or several — how should the work be split? — A: Six phases: P1 relicense + agent-capture retirement; P2 accounts/tenancy/projects core; P3 feedback API v2 + search + usage monitoring; P4 web app (tenant dashboard + project detail pages); P5 CLI + agent-first onboarding; P6 landing page + production deploy.
- Q: Web stack for the new user-facing surfaces? — A: One new Next.js app in the style of hi2vi_web with the Claude design-gate workflow; the packaged same-origin operator admin UI retires (affects P4/P6, recorded here for shared context).

## Notes

- Deliberately left to this phase's DECOMP: search engine choice (Postgres full-text search vs an external engine such as Meilisearch/Typesense) and the exact endpoint inventory.
- Builds on P2's tenants/projects/credentials model.
