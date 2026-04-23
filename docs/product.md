# Product

## Status

Vocky is pre-MVP. The first MVP scope is now defined, but the product is not implemented yet.

## Summary

Vocky is a feedback layer for agent products. It aims to capture user feedback from agent conversations, structure it into usable signals, and help teams understand what customers are asking for, praising, or struggling with.

## First MVP

The first MVP is intentionally narrow:

- Self-hosted and single-tenant
- MCP-only ingestion for feedback capture
- Raw feedback storage with basic metadata
- A minimal review/query API for record retrieval and simple counts or trends

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

- Capture feedback events from agent interactions through MCP
- Store raw feedback with enough metadata for later review
- Make stored feedback reviewable through a minimal query surface
- Surface simple counts and trends without building a full analytics product
- Keep the first release practical for community and self-hosted use

## Non-Goals for Now

- Automatic classification or taxonomy assignment
- A human-facing dashboard UI
- A production-ready analytics suite
- Non-MCP ingestion paths
- Multi-tenant managed-cloud architecture
- Enterprise-grade compliance or admin workflows
- Finalized public API commitments

## Product Direction

- Community and self-hosted usage are part of the base direction.
- The first MVP should optimize for self-hosted deployment before managed concerns.
- A managed offering may exist later around convenience, operations, and richer workflows.
- The repo should stay honest about what is planned versus what is already implemented.

## Terminology

- `VoC`: voice of customer
- `phase`: a grouped unit of work in `works/backlog.md`
- `slice`: a concrete step inside a phase
- `work item`: a timestamped execution folder under `works/current/` or `works/archives/work_items/`
