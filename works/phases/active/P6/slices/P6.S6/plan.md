# P6.S6 — Edge nginx vhost (`deploy/vocky.conf`) · plan

> Slice `P6.S6` (implementation, risk **HIGH**). Highest blast radius in the phase: the edge `conf.d/`
> tree is tested + reloaded **as a unit**, so a house-rule violation breaks **every** co-tenant site
> (changple5, knowledge, hi2vi). Authored here; applied on the box at S10 behind a hard `nginx -t` gate.
> Read `phase.md` (Findings + Constraints — especially the nginx house rules).

## Context

`vocky.hi2vi.com` needs a vhost on the standalone `edge` (`/home/opc/edge/conf.d/`, container `edge-nginx`)
that TLS-terminates and reverse-proxies by path to the S5 containers over `changple_shared_network`. Model:
**`~/projects/personal/knowledge/deploy/knowledge.conf`** (proven; read it in full). Vocky differs: **two
upstreams** (`vocky-api:8000`, `vocky-web:3000`) — `/mcp` is **in-app on vocky-api**, no mcp container —
plus an extra Next BFF prefix `/api/app/` alongside `/api/auth/`.

## Create — `deploy/vocky.conf`

Faithful adaptation of `knowledge.conf`, with a header comment (what it is, where it lands, the apply path
`scp … oracle-cloud:/home/opc/edge/conf.d/vocky.conf` → `ssh oracle-cloud 'cd /home/opc/edge && ./validate.sh && ./deploy.sh'`, and the HOUSE RULES).

**`:80`** — `listen 80; server_name vocky.hi2vi.com; return 301 https://$host$request_uri;`

**`:443`** — `listen 443 ssl; http2 on; server_name vocky.hi2vi.com;`
- **TLS:** `ssl_certificate /etc/nginx/certs/hi2vi.crt; ssl_certificate_key /etc/nginx/certs/hi2vi.key;`
  (wildcard `*.hi2vi.com` already covers `vocky.hi2vi.com`).
- **Docker DNS re-resolution (load-bearing):** `resolver 127.0.0.11 valid=30s ipv6=off; resolver_timeout 5s;`
  + `set $vocky_api vocky-api; set $vocky_web vocky-web;` and **variable** `proxy_pass` everywhere.
- **Cloudflare real-IP restore:** the full `set_real_ip_from` CF v4+v6 list **verbatim from knowledge.conf**
  + `real_ip_header CF-Connecting-IP;`.
- **`add_header Strict-Transport-Security "max-age=300" always;`** (short, no includeSubDomains/preload) +
  additive **`add_header Content-Security-Policy "upgrade-insecure-requests" always;`** (composes with the
  app CSP from S3). No `location` sets its own `add_header`.
- **`client_max_body_size 12m;`** — attachments upload **one-per-request** via `POST /api/feedback/attachments`
  (≤ 5 MiB each; the capture references them by id), so 12m is comfortable headroom — not a 10×5 MiB batch.
- **Hoisted `proxy_set_header`** at server level (`Host`, `X-Real-IP`, `X-Forwarded-For`, `X-Forwarded-Proto`,
  `proxy_http_version 1.1`, `Connection ""`) with the HEADER-INHERITANCE FOOTGUN comment: **every location
  sets NONE**.

**Routing (longest-prefix wins; variable upstream, no per-location headers):**
| location | → upstream | notes |
|---|---|---|
| `= /healthz` | `$vocky_api:8000` | exact |
| `/api/auth/` | `$vocky_web:3000` | Next BFF; beats `/api/` |
| `/api/app/` | `$vocky_web:3000` | Next BFF attachment proxy; beats `/api/` |
| `/api/` | `$vocky_api:8000` | vk_ capture + project read/manage |
| `/auth/` | `$vocky_api:8000` | account auth (CLI + server-to-server) |
| `/app/` | `$vocky_api:8000` | session control plane |
| `/mcp` | `$vocky_api:8000` | **SSE-safe**: `proxy_buffering off; proxy_read_timeout 3600s; proxy_send_timeout 3600s;` |
| `/admin/` | `return 404;` | **not exposed** (api.md: "protect or avoid exposing `/admin/api`"); bearer-gated surface stays internal |
| `/` | `$vocky_web:3000` | catch-all: landing + authed UI + Next assets/metadata |

Fast routes use `proxy_connect_timeout 5s; proxy_read_timeout 60s;` (vocky has no slow git-push writes).
`/mcp` uses the SSE-safe long timeouts above.

## Decisions (approved with this plan)

- `/admin/api` **not exposed at the edge** (404) — bearer-gated, kept internal; SaaS ops go via `/app/*`.
- Public `/auth/*` has **no rate limit** (vocky has no server-side limiter; `limit_req_zone` is forbidden at
  the shared edge). Fine for launch behind Cloudflare; the orchestrator opens a **deferred job** for a
  Cloudflare rule / future in-process limiter. Record this as an Open Question in `phase.md`.

## Verification

- **nginx is not in the sandbox** — the real `nginx -t` runs on the box at S10. Here, do a careful static
  review matching `knowledge.conf` structurally, plus:
  - `grep -n "default_server\|listen \[::\]\|limit_req_zone" deploy/vocky.conf` → **empty**.
  - every `proxy_pass` uses the variable form (`http://$vocky_`), never a literal name or `upstream {}`.
  - `server_name vocky.hi2vi.com` on both blocks; cert `/etc/nginx/certs/hi2vi.crt`; CF ranges present; HSTS
    + upgrade-CSP present; the routing table matches line-for-line.
- `python3 scripts/workflow.py validate` passes (repo root — cwd may persist).

## Docs

Append a **Doc impact** note to `phase.md`: `deploy/vocky.conf` added (edge vhost, routing map, `/admin/api`
not exposed, HSTS + additive upgrade-CSP, CF real-IP, Docker DNS re-resolution, house-rule compliance).
Record the **/auth rate-limit gap** as an Open Question for the deferred job + REVIEW's
`operations.md`/`security.md` consolidation.

## Executor notes (high tier)

Match `knowledge.conf`'s structure and every load-bearing comment (resolver, footgun, house rules). Do
**not** add a `limit_req_zone`, `upstream {}`, `default_server`, IPv6 `listen`, or any per-location
`proxy_set_header`/`add_header`. Get the longest-prefix routing exactly right — a misroute (e.g.
`/api/app/` → api) silently breaks the BFF. If a route prefix isn't covered by the table, escalate rather
than guess. Write `result.md`; append the Doc-impact + /auth-gap notes to `phase.md`. Do not commit; do not
transition status.
