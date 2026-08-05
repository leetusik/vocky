# Result — P14.DECOMP

Decomposed P14 into four middle slices and seeded `phase.md` with the plan of record: the marker design, the sentiment+note field mapping, the hardening scope, and the research findings later slices need.

## Slices created (bare folders, no pre-filled `plan.md`)

| Slice | Name | Kind | Risk | Order | Depends on |
| --- | --- | --- | --- | --- | --- |
| `P14.S1` | Persist the `recorded_by` agent marker through the capture path | implementation | high | 1 | — |
| `P14.S2` | Expose `recorded_by` on every read, filter, and dashboard surface | implementation | high | 2 | `P14.S1` |
| `P14.S3` | End-to-end verification of agent-recorded capture | implementation | high | 3 | `P14.S2` |
| `P14.S4` | Public agent-feedback documentation: SKILL.md, README, doc impact | implementation | high | 4 | `P14.S3` |

Single pass — no visual design in scope, so no `co-work` slice and no `P14.DECOMP2`. Every slice is `high`: each writes real code or spans several files, and S4 edits two byte-identical SKILL copies plus the README and is the public contract itself, so it is not a single-file docs-prose edit.

Sequence: write path → read path → proof → publish, so the public documentation describes what has already been demonstrated.

## Decisions taken (full reasoning + rejected alternatives in `phase.md`)

- **D1 — the marker is a new nullable, indexed `feedback_events.recorded_by TEXT` column** with a closed `agent` | `human` vocabulary and `NULL` = unspecified. Rejected: a new `trigger_type` value (cheapest, but `trigger_type` is the *why* and the marker is the *who* — overloading it is lossy and un-first-class), `source.integration` convention (explicitly rejected by the operator), a boolean, and a JSONB key (neither indexed nor filterable). Validation mirrors `src/vocky/trigger.py`. Not added to the Admin PATCH allowlist — it is provenance, not a review field.
- **D2 — `/mcp` defaults `recorded_by` to `"agent"` when omitted; REST leaves it `NULL`.** `/mcp` is by construction the agent-runtime surface, so the default corrects the record rather than guessing; REST is genuinely mixed, so `NULL` is the honest answer and every existing REST client stays byte-for-byte unchanged. The default lives in `normalize_mcp_payload`, never in the transport-neutral `_normalize_capture_payload`.
- **D3 — sentiment → `message`, note → `comment`; no new text columns.** Both fields already exist on every surface and, decisively, are **both already inside the `pg_trgm` search expression**, so the free-text sentiment and note become searchable (Korean included) with zero index work. `intent.md`'s "the note is a hard requirement" is read as a *capability* requirement ("must be able to pass"), so `comment` is documented as required for agent capture rather than server-enforced — enforcing it would 400 every existing client.
- **D4 — hardening: one item verified, two deferred.** Prod `VOCKY_MCP_ALLOWED_HOSTS` is **already set** (`compose.prod.yml:143` → `vocky.hi2vi.com`) and `VOCKY_MCP_ALLOWED_ORIGINS` is correctly unset (non-browser MCP clients send no `Origin`) — verify only, no change. Deferred with recommended `defer-job` titles and triggers recorded in `phase.md`: (a) per-credential rate limiting on `/api/feedback` + `/mcp` (the existing limiter is per-IP, which is exactly wrong for server-to-server agent traffic — real design work, not a one-liner), (b) capture-only key scopes, revisiting D-P3-2 now that unscoped `vk_` keys will live in third-party agent runtimes. S4 must state the current unscoped-key reality plainly in the public docs rather than let readers assume otherwise.
- **Out of scope, recorded explicitly:** any new dashboard visual control (that is Claude Design's job under `design-cowork`), backfilling legacy rows, a sentiment enum, changple-side integration (changple5 P63), and prod deployment.

## Findings seeded into `phase.md`

The write path's five must-touch places (notably the hand-written `capture_queue` serialize **and** deserialize, where a dropped field fails silently); the MCP tool's separate flat parameter list, which a base-model field does **not** reach; the read path's one filter site plus two duplicated normalizers/serializers covering four REST surfaces; the web dashboard's URL-param allowlist vs its three-input form; the migration template plus the head-revision pin at `tests/test_persistence.py:45` and the pre-existing `alembic check` drift whitelist item; the `scripts/skill_parity.py` byte gate and why the served copy is never hand-edited; the `uv` + real-Postgres test environment; and the additivity acceptance bar (no existing assertion may need editing).

## Validation

| Command | Outcome |
| --- | --- |
| `python3 scripts/workflow.py new-slice --phase P14 --slice P14.S{1,2,3,4} ...` (×4) | pass — four bare slice folders created, each holding only `slice.json` |
| `python3 scripts/workflow.py validate` | pass — `Workflow validation passed.` |
| `python3 scripts/workflow.py next` | pass — `next_slice=P14.S1` |

## Deviations from `plan.md`

None. The plan sketched "schema/marker + capture seam → surface exposure (REST + MCP) → tests/verification → public docs" and invited merging or splitting; the research moved the MCP tool parameter into the first slice so the seam is "the whole write path" rather than splitting REST and MCP capture across two slices, and folded the small web TypeScript plumbing into the read-path slice. Four slices, same shape.

## Doc impact

None from this slice (no durable-truth change; the design decisions are recorded in `phase.md` and will reach `decisions.md` through the implementation slices' notes, consolidated at `P14.REVIEW`).

## Notes for the orchestrator

- Two `defer-job`s are recommended but **not** filed — DECOMP may not run `defer-job`. Titles, reasons, and triggers are in `phase.md` → "D4 — Hardening scope".
- Two open questions are parked in `phase.md` for the operator at REVIEW: whether `comment` should eventually be server-enforced for agent capture, and whether to file the two deferred hardening items now.
- `P14.S3` needs a running local stack (`make compose-up` + a separate `TEST_DATABASE_URL`); if the operator's stack is not up, that slice will need it before it can prove anything.
