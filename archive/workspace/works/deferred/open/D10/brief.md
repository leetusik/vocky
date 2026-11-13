# Deferred: D10 Per-credential permission scopes (capture-only keys) — revisit D-P3-2 now that vk_ keys live in third-party agent processes

## Context

## Why Deferred

Under D-P3-2 one vk_ key does capture + read + PATCH + DELETE across its whole scope; P14 puts exactly that key inside third-party agent runtimes. A capture-only scope is the right answer but touches minting, middleware, and every /api/* handler — a phase, not a slice

## Trigger to Promote

before recommending vocky keys be embedded in any third-party runtime the operator does not control

## Notes

