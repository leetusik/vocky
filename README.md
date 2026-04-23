# vocky

Feedback MCP for agents. Turn customer conversations into structured voice-of-customer signals.

Vocky is in the early planning and pre-MVP stage.

## What Vocky Is

Vocky is a Model Context Protocol (MCP)-based feedback layer for agent products. The idea is simple: when users talk to an AI agent, they often reveal bugs, friction points, requests, and positive reactions. Vocky aims to capture those moments, structure them, and make them useful.

The name comes from VoC, short for voice of customer.

## Why It Exists

- Agent conversations already contain valuable product feedback.
- Most of that feedback gets lost in logs, transcripts, or support noise.
- Teams need a simple way to turn conversational feedback into product insight.

## What It Will Do First

- Capture feedback events from agent interactions through MCP
- Store raw feedback with basic metadata for later review
- Expose a minimal review/query API for retrieving records and simple counts
- Run as a self-hosted, single-tenant MVP

## What The First MVP Will Not Do

- Automatic classification or taxonomy assignment
- A dashboard UI
- Non-MCP ingestion paths
- Managed multi-tenant SaaS features

## Open Source + Managed Direction

Vocky is intended to follow a light open-core direction: a community, self-hostable base and a managed cloud offering later. The goal is to keep the core transparent and usable while building a hosted product around convenience, operations, and richer workflows.

## Current Status

- This repo is the initial public home for the project direction and upcoming implementation.
- The first MVP scope is defined, but implementation has not started yet.
- There is no production-ready server yet.
- There is no install guide yet.
- There is no stable public API or tool contract yet.

## License

Vocky is licensed under the GNU Affero General Public License v3.0. See [LICENSE](./LICENSE).
