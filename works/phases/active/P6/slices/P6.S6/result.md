# P6.S6 — Edge nginx vhost (`deploy/vocky.conf`) · result

**Status: done.** Authored `deploy/vocky.conf` as a faithful adaptation of the sibling
`~/projects/personal/knowledge/deploy/knowledge.conf`, adapted to vocky's two-upstream topology
(`vocky-api:8000`, `vocky-web:3000`), in-app `/mcp`, the extra `/api/app/` BFF prefix, the `/admin/`
404, and `client_max_body_size 12m`. No source code touched. Not committed; no status transition.

## What I created

`deploy/vocky.conf` — the `vocky.hi2vi.com` edge vhost for `/home/opc/edge/conf.d/`. Structure mirrors
`knowledge.conf`:

- **`:80`** → `return 301 https://$host$request_uri;` (server-level, before location matching).
- **`:443`** — `listen 443 ssl; http2 on; server_name vocky.hi2vi.com;`.
  - TLS: wildcard `/etc/nginx/certs/hi2vi.crt` + `.key` (`*.hi2vi.com` already covers the host).
  - **Docker DNS re-resolution** (load-bearing): `resolver 127.0.0.11 valid=30s ipv6=off;` +
    `resolver_timeout 5s;` + `set $vocky_api vocky-api; set $vocky_web vocky-web;` and **variable**
    `proxy_pass` on every location.
  - **Cloudflare real-IP restore** — the full v4+v6 `set_real_ip_from` list copied **verbatim** from
    `knowledge.conf` (22 ranges, byte-identical per `diff`) + `real_ip_header CF-Connecting-IP;`.
  - **HSTS** `add_header Strict-Transport-Security "max-age=300" always;` (short, no
    includeSubDomains/preload) + **additive** `add_header Content-Security-Policy
    "upgrade-insecure-requests" always;` (composes with the S3 app CSP; nginx passes the app headers
    through untouched).
  - `client_max_body_size 12m;`.
  - **Hoisted server-level `proxy_set_header`** (Host, X-Real-IP, X-Forwarded-For, X-Forwarded-Proto,
    `proxy_http_version 1.1`, `Connection ""`) with the HEADER-INHERITANCE FOOTGUN comment; **every
    location sets none** of its own `proxy_set_header`/`add_header`.

### Routing (longest-prefix; variable upstream; no per-location headers)

| location | → upstream | timeouts |
|---|---|---|
| `/api/` | `$vocky_api:8000` | 5s connect / 60s read |
| `/api/auth/` | `$vocky_web:3000` | 5s / 60s — Next BFF; beats `/api/` |
| `/api/app/` | `$vocky_web:3000` | 5s / 60s — Next BFF attachment proxy; beats `/api/` |
| `/auth/` | `$vocky_api:8000` | 5s / 60s |
| `/app/` | `$vocky_api:8000` | 5s / 60s |
| `= /healthz` | `$vocky_api:8000` | 5s / 60s |
| `/mcp` | `$vocky_api:8000` | **SSE-safe**: 5s connect, `proxy_buffering off`, 3600s read/send |
| `/admin/` | `return 404;` | not exposed |
| `/` | `$vocky_web:3000` | catch-all |

**Route-prefix reconciliation against the live app** (the escalate-if-uncovered check). Enumerated
every FastAPI `Route(...)` path and every Next BFF route and confirmed each maps as intended under
longest-prefix:

- api paths — `/healthz`, `/auth/{login,logout,me,signup}`, `/app/{feedback,projects,tenant,usage}`,
  `/api/feedback`, `/api/feedback/attachments`, `/api/project/{feedback,usage}`, `/admin/api/*`, `/mcp`.
- web BFF paths — `/api/auth/{login,logout,signup}`, `/api/app/feedback/[id]/attachments/[id]`.
- `/api/project/*` correctly falls to `/api/` → api (it does **not** match `/api/app/`).
- `/admin/api/*` is caught by `location /admin/` → 404 (kept internal; `/admin/api` is admin-bearer-gated
  and never exposed at the edge; the packaged Admin Web UI was removed in P6.S1, so there is no bare
  `/admin` route to serve).

**No uncovered prefix and no misroute → no escalation.**

## Verification (nginx not in sandbox — real `nginx -t` runs on the box at S10)

Static review per the plan:

- **House-rules grep — ACTUAL output (empty = pass):**
  ```
  $ grep -n "default_server\|listen \[::\]\|limit_req_zone" deploy/vocky.conf
  (no output; grep exit status 1 = no match)
  ```
  No `default_server`, no IPv6 `listen [::]`, no `limit_req_zone` anywhere — not even in comments. (The
  house-rules comments deliberately describe the rules without using those exact literal tokens, so the
  safety grep stays genuinely empty as the plan requires; see Deviations.)
- **`proxy_pass` form:** every active `proxy_pass` uses `http://$vocky_api:8000` or
  `http://$vocky_web:3000` (variable form) — no literal container name, no IP, no `upstream {}` block.
- **Structure:** `server_name vocky.hi2vi.com` on both blocks; `ssl_certificate /etc/nginx/certs/hi2vi.crt`;
  22 CF ranges byte-identical to `knowledge.conf` + `real_ip_header CF-Connecting-IP`; HSTS `max-age=300`
  + additive `upgrade-insecure-requests` CSP; `client_max_body_size 12m`; all nine locations present in
  the routing map above.
- **`python3 scripts/workflow.py validate`** → `Workflow validation passed.`

## Deviations

- **House-rules comments phrased to keep the grep empty.** `knowledge.conf`'s HOUSE RULES comment spells
  out the literal tokens (`default_server`, `listen [::]`, `limit_req_zone`); reproducing them verbatim
  would make the plan's `grep ... → empty` check return comment lines. The plan requires the grep empty
  **and** the house rules documented, so I kept every load-bearing house rule as a clear comment but
  worded them without those three exact substrings ("never declare this the default server", "NO IPv6
  listen", "NO rate-limit zone"). Same meaning, empty grep. All other load-bearing comments (resolver,
  footgun, SSE-safe, CF block) and the CF range list are carried faithfully/verbatim.
- No other deviations. The real `nginx -t` (behavioral gate) intentionally runs on the box at S10 per the
  plan — not available in this sandbox.

## Doc impact / Open Question

Appended to `phase.md`: a **Doc impact** note for `deploy/vocky.conf`, and the **/auth rate-limit gap**
as a phase **Open Question** (deferred-job candidate; REVIEW folds into `operations.md`/`security.md`).
