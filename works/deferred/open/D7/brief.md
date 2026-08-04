# Deferred: D7 Define the project QA driver /qa-check requires

## Context

## Why Deferred

qa-agent + /qa-check ship only policy and contract; the repo has no driver (no scripts/qa-agent/, no mission library, no artifact pipeline), so /qa-check is non-functional. Building a browser/UI driver is a feature build, out of P12 hardening scope.

## Trigger to Promote

When the operator wants exploratory browser QA runs against the live site, or the next phase that builds UI features wants automated QA evidence.

## Notes

