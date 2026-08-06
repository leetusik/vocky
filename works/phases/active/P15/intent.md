# Intent — P15

- Captured at: 2026-08-06T22:20:21+09:00
- Origin: operator

## Original Input (verbatim)

> to understand what vocky is for general users(developers). we can make several knowledge  for this. each slice will be create knowledge. using /explain skill. in the phase, include update  readme.md if it's outdated. and maybe good to create for maintainer, and contributor would be good  also.

## Confirmed Intent (refined + clarified)

Give a new maintainer full understanding of vocky through a series of `/explain` knowledge explainers saved to the operator's personal knowledge base. One explainer will not be enough — the `DECOMP` slice surveys `docs/current/*.md` and the codebase and cuts one slice per knowledge topic, as many as full coverage of the system requires. The phase also includes a slice that audits `README.md` (last updated 2026-08-05, 476 lines) against current reality and updates whatever is stale or missing — an audit-and-fix, not a rewrite.

Execution note: `/explain` is a main-thread-only skill, so the knowledge slices are run inline by the orchestrator (like design slices) rather than dispatched to a `slice-executor`; the README audit slice is dispatched normally.

## Clarifications Resolved

- Q: Which audiences should the explainers cover (users/developers, maintainers, contributors)? — A: "maybe only for the maintainer. the new one. full understanding. it could be not be done with only one knowledge" — target a **new maintainer** needing full understanding; multiple explainers expected.
- Q: Should the knowledge live in the personal KB via `/explain`, or as repo docs? — A: Personal KB via `/explain`, as the skill is designed.
- Q: Decide explainer topics now, or leave to `DECOMP`? — A: Let `DECOMP` decide.
- Q: How to handle README.md, given it was updated yesterday? — A: Audit and update only what's stale or missing.

## Notes

- The original request mentioned general users (developers) and contributors as possible audiences; the confirmed scope narrows to the new-maintainer audience. User/contributor-facing knowledge can be a later phase or deferred job if wanted.
