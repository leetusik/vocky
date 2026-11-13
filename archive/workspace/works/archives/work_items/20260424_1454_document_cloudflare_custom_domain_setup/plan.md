# Plan

- Work item: works/current/20260424_1454_document_cloudflare_custom_domain_setup
- Created at: 20260424_1454
- Phase ID: P1
- Phase: Public custom-domain MCP access
- Slice ID: P1.S4
- Slice: document Cloudflare custom-domain setup

## Context

The code now supports a public MCP host, optional bearer auth, and authenticated smoke checks. Operators still need clear docs for using `vocky.example.com` through Cloudflare and registrar.

## Goal

Document the public custom-domain deployment path clearly enough for an operator who owns `example.com` at registrar and has not set up Cloudflare before.

## Scope

- In scope:
  - Update README operator steps for Cloudflare full DNS setup, registrar nameservers, Cloudflare Tunnel, Vocky env vars, and public smoke.
  - Update architecture docs with the new config surface and public access mode.
  - Update API docs with bearer-token expectations for public MCP consumers.
  - Update product docs if needed to reflect optional public self-hosted usage.
- Out of scope:
  - Automating Cloudflare account, DNS, or tunnel creation.
  - Adding Cloudflare Access or OAuth.

## Approach

Keep README practical and command-oriented. Keep durable system truth in `docs/architecture.md` and public consumer contract changes in `docs/api.md`.

## Affected Files

- `README.md`
- `docs/product.md`
- `docs/architecture.md`
- `docs/api.md`
- `works/backlog.md`
- Work item plan/result files

## Reference Docs To Review

- Cloudflare domain onboarding and nameserver update docs.
- Cloudflare Tunnel overview, routing, local tunnel, and configuration-file docs.
- registrar nameserver change docs.

## Risks and Open Questions

- The actual Cloudflare nameserver names are assigned per Cloudflare zone and cannot be hard-coded.
- Public smoke cannot pass until the external Cloudflare and tunnel state exists.

## Verification Plan

- Run `rg` over docs for the new env vars, public URL, and stale redirect wording.
- Run focused tests again after docs.

## Planned Commits

- `docs(public-access): document cloudflare custom domain setup`
