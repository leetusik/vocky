# Product

## Status

Vocky is pre-MVP. The first runnable self-hosted capture plus review service is implemented with MCP capture/read tools, server-to-server REST capture, liked-conversation retrieval, Admin REST, PostgreSQL persistence, Redis-backed queueing, and a background worker. The contracts should still be treated as early-stage.

## Summary

Vocky is a feedback layer for agent products. It aims to capture user feedback from agent conversations, structure it into usable signals, and help teams understand what customers are asking for, praising, or struggling with.

## First MVP

The first MVP is intentionally narrow:

- Self-hosted and single-tenant
- MCP and server-to-server REST ingestion for feedback capture
- Async capture that accepts quickly over MCP or REST and persists in the background
- Explicit user action feedback capture, including like/dislike values, optional comments, conversation context, and basic metadata
- MCP review/query tools for record retrieval, simple counts, trends, and liked-conversation retrieval
- Dedicated Admin REST endpoints for human/operator review of stored feedback
- PostgreSQL storage with Redis-backed background persistence

The MVP does not need automated classification, a dashboard UI, or managed-cloud capabilities.

## Target Users

- Teams building agent-based products
- Developers integrating feedback capture into agent workflows
- Product and operations teams reviewing customer voice from agent interactions

## Problem

- Agent conversations contain product feedback that usually gets buried in logs.
- Teams need structured feedback, not raw transcript noise.
- Feedback should be reviewable, trendable, and usable for prioritization.

## Goals

- Capture feedback events from agent interactions through MCP or server-to-server REST without making clients wait on persistence
- Store explicit user action feedback with enough message, context, comment, and metadata detail for later review
- Make stored feedback reviewable through a minimal query surface
- Surface simple counts and trends without building a full analytics product
- Keep the first release practical for community and self-hosted use

## Non-Goals for Now

- Automatic classification or taxonomy assignment
- A human-facing dashboard UI
- A production-ready analytics suite
- Browser-direct unauthenticated ingestion paths
- Public REST review, query, summary, or management APIs outside the dedicated Admin REST surface
- Multi-tenant managed-cloud architecture
- Enterprise-grade compliance or admin workflows
- Finalized public API commitments

## Product Direction

- Community and self-hosted usage are part of the base direction.
- The first MVP should optimize for self-hosted deployment before managed concerns.
- Self-hosted deployments may be local/private or publicly reachable behind an operator-managed custom domain, provided public MCP, REST capture, and Admin REST access are protected where exposed.
- The capture path should acknowledge accepted work quickly and complete persistence asynchronously in the background.
- The initial high-signal capture path should focus on explicit user actions, such as like/dislike clicks and optional comments, rather than trying to infer feedback from every conversation turn.
- A managed offering may exist later around convenience, operations, and richer workflows.
- The repo should stay honest about what is planned versus what is already implemented.

## Terminology

- `VoC`: voice of customer
- `phase`: a grouped unit of work in `works/backlog.md`
- `slice`: a concrete step inside a phase
- `work item`: a timestamped execution folder under `works/current/` or `works/archives/work_items/`
