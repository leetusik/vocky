# API

## Status

There is no stable public API or tool contract yet. The draft MVP surfaces below exist to guide implementation and should not be treated as shipped commitments.

## Purpose

Use this file to record real public-facing contracts once they exist. Until then, treat this document as a place to define how contracts should be documented, not as a promise of shipped interfaces.

## Draft MVP Surfaces

- MCP tool contracts for feedback capture
- A minimal service API for review and query access

## Documentation Rules

- Only document a contract as stable when it is implemented or explicitly accepted.
- Mark experimental surfaces as draft.
- Record breaking changes once external consumers exist.
- Keep implementation notes out of this file unless they affect consumers.

## Contract Template

### Surface Name

- Status:
- Consumers:
- Purpose:
- Inputs:
- Outputs:
- Errors:
- Auth or permissions:
- Notes:

## Draft Contracts

### Feedback Capture MCP Tool

- Status: draft
- Consumers: Agent products and agent-runtime integrations sending feedback into Vocky
- Purpose: Submit a single feedback event from an agent interaction for storage
- Inputs:
  - Raw feedback content or message
  - Source metadata identifying the product or integration
  - Conversation or session context when available
  - Event time or caller context
  - Optional caller-provided tags or attributes
- Outputs:
  - Acceptance acknowledgement
  - Stored feedback identifier
  - Normalized creation timestamp
- Errors:
  - Invalid or incomplete payload
  - Unsupported input shape
  - Storage unavailable or write failed
  - Unauthorized, if the deployment requires it
- Auth or permissions:
  - Deployment-specific for the self-hosted MVP
  - No managed-cloud auth model is defined yet
- Notes:
  - MCP is the only ingestion surface in the first MVP
  - The MVP stores raw feedback and metadata; it does not auto-classify events

### Review Query API

- Status: draft
- Consumers: Operators, scripts, or future UI layers reviewing stored feedback
- Purpose: Retrieve stored feedback records and simple aggregates without requiring a dashboard
- Inputs:
  - Record-list queries with simple filters such as time range, source, conversation or session identifiers, or tags when available
  - Summary queries for simple counts or trends over a time window
- Outputs:
  - Filtered feedback records with stored metadata
  - Simple aggregates such as counts over time or by supported metadata dimensions
- Errors:
  - Invalid filter or unsupported aggregation request
  - Storage unavailable or read failed
  - Unauthorized, if the deployment requires it
- Auth or permissions:
  - Deployment-specific for the self-hosted MVP
- Notes:
  - This is a machine-readable review surface, not a human-facing dashboard
  - Classification outputs are out of scope for the first MVP
