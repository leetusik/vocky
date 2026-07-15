# Intent — P4

- Captured at: 2026-07-15T14:55:54+09:00
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

This phase (P4) covers the authenticated web app:

- Build the tenant dashboard and project detail pages as an authenticated web app.
- Stack: a new Next.js app in the style of `~/projects/personal/hi2vi_web` (same app that will later carry the P6 landing page), talking to the vocky REST API.
- The packaged same-origin operator Admin Web UI retires — this app replaces it as the browser surface.

## Clarifications Resolved

- Q: One phase or several — how should the work be split? — A: Six phases: P1 relicense + agent-capture retirement; P2 accounts/tenancy/projects core; P3 feedback API v2 + search + usage monitoring; P4 web app (tenant dashboard + project detail pages); P5 CLI + agent-first onboarding; P6 landing page + production deploy.
- Q: Web stack for the new user-facing surfaces (landing, dashboard, project pages)? — A: One new Next.js app, hi2vi_web-style, with the Claude design-gate workflow; the packaged admin UI retires.

## Notes

- Builds on P2 (accounts/tenancy) and P3 (API v2, search, usage monitoring) — the dashboard surfaces those.
- The Claude design-gate workflow from hi2vi_web applies to this app's design work as well as the P6 landing page.
