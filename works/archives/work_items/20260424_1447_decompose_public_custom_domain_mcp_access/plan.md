# Plan

- Work item: works/current/20260424_1447_decompose_public_custom_domain_mcp_access
- Created at: 20260424_1447
- Phase ID: P1
- Phase: Public custom-domain MCP access
- Slice ID: P1.DECOMP
- Slice: decompose phase

## Context

The current app is reachable over Tailscale for `/healthz`, but the public MCP path is not client-ready:

- `/mcp` redirects to `/mcp/` with an `http://` Location.
- `/mcp/` returns `421 Invalid Host header` when accessed through the external hostname.
- A LangChain workaround succeeds only by sending `Host: 127.0.0.1:8000`.

The user wants Vocky reachable everywhere through the custom domain `vocky.example.com`, and chose public access with bearer-token protection.

## Goal

Decompose the phase into implementation slices that make `https://vocky.example.com/mcp` usable by normal MCP clients without Host-header workarounds while keeping public exposure protected.

## Scope

- In scope:
  - Replace the placeholder backlog with a dedicated public custom-domain phase.
  - Lock the route, host validation, auth, smoke, docs, and review slices.
  - Record Cloudflare Tunnel and registrar setup expectations for later docs.
- Out of scope:
  - Code changes beyond backlog/work-item planning.
  - Live Cloudflare, registrar, or tunnel state changes.

## Approach

Use one active phase with four middle slices:

- `P1.S1`: FastMCP transport security and `/mcp` route behavior.
- `P1.S2`: Bearer-token protection for MCP traffic.
- `P1.S3`: Public smoke support and examples.
- `P1.S4`: Cloudflare custom-domain documentation.

Keep `P1.REVIEW` open until local tests and public-readiness checks pass.

## Affected Files

- `works/backlog.md`
- `works/current/20260424_1447_decompose_public_custom_domain_mcp_access/plan.md`
- `works/current/20260424_1447_decompose_public_custom_domain_mcp_access/result.md`

## Reference Docs To Review

- `docs/product.md`
- `docs/architecture.md`
- `docs/api.md`
- Cloudflare domain onboarding, nameserver, and Tunnel routing docs.
- registrar nameserver change docs.

## Risks and Open Questions

- The app currently has no auth, so public exposure must not be completed without a bearer-token gate.
- Cloudflare and registrar setup is operator state outside the repo; the repo can document it and provide smoke checks, but cannot complete account setup itself.

## Verification Plan

- Confirm `works/backlog.md` has concrete `P1` slices and no placeholder slice remains.
- Archive the decomposition work item after result completion.

## Planned Commits

- `chore(workflow): add public custom-domain access backlog`
