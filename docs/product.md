# Product

## Status

Vocky is pre-MVP. This repo currently contains planning, workflow scaffolding, and early product framing.

## Summary

Vocky is a feedback layer for agent products. It aims to capture user feedback from agent conversations, structure it into usable signals, and help teams understand what customers are asking for, praising, or struggling with.

## Target Users

- Teams building agent-based products
- Developers integrating feedback capture into agent workflows
- Product and operations teams reviewing customer voice from agent interactions

## Problem

- Agent conversations contain product feedback that usually gets buried in logs.
- Teams need structured feedback, not raw transcript noise.
- Feedback should be reviewable, trendable, and usable for prioritization.

## Goals

- Capture feedback events from agent interactions
- Classify feedback into a small usable taxonomy
- Store feedback with enough context for later review
- Surface simple summaries and trends

## Non-Goals for Now

- A production-ready analytics suite
- Finalized public API commitments
- Enterprise-grade compliance or admin workflows
- A complete managed SaaS specification

## Product Direction

- Community and self-hosted usage are part of the base direction.
- A managed offering may exist later around convenience, operations, and richer workflows.
- The repo should stay honest about what is planned versus what is already implemented.

## Terminology

- `VoC`: voice of customer
- `phase`: a grouped unit of work in `works/backlog.md`
- `slice`: a concrete step inside a phase
- `work item`: a timestamped execution folder under `works/current/` or `works/archives/work_items/`
