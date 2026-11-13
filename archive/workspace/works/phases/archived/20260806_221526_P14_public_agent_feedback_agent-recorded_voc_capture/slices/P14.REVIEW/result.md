# Result — P14.REVIEW: Phase review and durable-doc consolidation

**Verdict: `pass`.** P14 delivered exactly what `intent.md` asked for, every gate is green, and the
phase's durable-truth changes are consolidated into **eleven** new doc versions. No source file was
touched by this slice.

---

## 1. Validation — all slices together

Run from the repo root against the live compose stack (`vocky-postgres`, `vocky-redis`, `vocky-app`,
`vocky-worker`, all up and healthy).

| Command | Result |
|---|---|
| `make test` (full Python suite) | **238 passed** in 9.5s — matches the S2/S3/S4 baseline exactly |
| `make check-skill-parity` | **PASS** — `web/public/SKILL.md` byte-identical to the canonical |
| `cd web && npm test` | **78 passed / 10 files** |
| `cd web && npm run typecheck` | clean |
| `cd web && npm run lint` | clean |
| `cd web && npm run format:check` | clean — "All matched files use Prettier code style!" |
| `uv run alembic check` | **only** the known pre-existing `remove_index ix_feedback_events_search_trgm` drift; no `add_column` / `add_index`, so `recorded_by` + its index match the ORM exactly |
| `uv run alembic current` | `20260805_1200 (head)` |
| `make smoke` | **PASS** — `healthz ok`, `POST /api/feedback accepted`, `GET /api/feedback ok: 1 record(s)` (the reference payload now carries the marker) |
| `python3 scripts/workflow.py validate` | `Workflow validation passed.` |
| `make test` + `make check-skill-parity` re-run **after** doc consolidation | 238 passed / PASS — docs-only changes, as expected |

`pytest --collect-only` reports **238 tests across 30 files** (P13 baseline: 225 / 30) — P14 added 13
cases and **no new test file**, which matches the repo's terse-tests rule.

## 2. Spot-checks of the slices' claims against the tree

Sampled rather than re-implemented; every claim I sampled held.

- **All five write-path places threaded** (`grep -rn recorded_by src/`): `capture.BaseCaptureFeedbackInput`,
  `_normalize_capture_payload`, `CreateFeedbackEvent`, **both** `capture_queue._serialize_payload` and
  `_deserialize_payload`, and `repository.create_feedback_event` + `_to_record`, plus
  `persistence/models.py` (column + `__table_args__` index) and `FeedbackEventRecord`.
- **The MCP tool has the explicit flat parameter** (`tools/capture_feedback.py:43`) — without it the
  tool schema would not advertise the field at all — and `capture.py:335` stamps
  `MCP_DEFAULT_RECORDED_BY` only inside `normalize_mcp_payload`, leaving `_normalize_capture_payload`
  transport-neutral. Confirmed.
- **Read path complete**: `_apply_filters` predicate at `repository.py:593`, both normalizers
  (`admin_api.py:147` covering three surfaces, `api.py:173` the duplicate) and both serializers
  (`query_feedback_common.py:188`, `api.py:205`).
- **`recorded_by` is NOT in the Admin PATCH allowlist** — the handler's six `model_fields_set` branches
  are `feedback_value`, `comment`, `channel`, `tags`, `source_metadata`, `attributes`. Correct per D1.
- **Migration + pins**: `alembic/versions/20260805_1200_add_feedback_recorded_by.py` with a mirrored
  `downgrade`; `tests/test_persistence.py:45` pins the new head and line 53 lists the new index;
  `tests/test_accounts_provisioning.py:156` documents the by-revision downgrade pin.
- **Web**: `recorded_by` in `PARAM_KEYS` + `toQuery` + `VockyFeedback` + `VockyFeedbackQuery`, one
  `<Field>` row on the detail page, the `recordedBy` label in `content/feedback.ts`. **No entry in
  `FORM_FIELD_KEYS`** — the "no new rendered control" boundary held.
- **Public docs**: `SKILL.md` has exactly 8 numbered sections with the field-mapping step at 3, before
  the transports. S3's must-nots hold — every `q` mention in `README.md` / `docs/cli.md` /
  `SKILL.md` is scoped to `/app/feedback?q=` or `vocky feedback search`, and no CLI marker flag is
  implied anywhere.
- **D9 and D10 exist** under `works/deferred/open/` with the D4 titles, reasons, and triggers, both
  `source: P14.DECOMP`. The hardening open question is genuinely closed.

## 3. Judgment against the objective and `intent.md`

| Requirement (`intent.md` Confirmed Intent) | Verdict |
|---|---|
| Free-text sentiment **and** note, no enum | **Met.** `message` carries the user's words verbatim, `comment` the agent's note; no new columns, no vocabulary. Both are inside the `pg_trgm` search expression, verified live on Korean substrings (`감사`, `도움이 되었어요`, `수출 흐름`) with a clean negative control. |
| "The note argument is a **hard requirement**" | **Met as a capability, which is what the intent states** ("must be able to pass"). `comment` is passable on **every** capture surface — REST, MCP, and `vocky capture --comment` — and is documented as required for agent capture in SKILL.md, README, and `docs/cli.md`. Server enforcement was correctly *not* added; see the open question below. |
| First-class agent-vs-human marker, queryable/filterable | **Met.** A real nullable indexed column, not a convention: returned on all four read surfaces, filterable on all four list surfaces, and surfaced in the dashboard as a URL filter + a detail row. Proven live at the storage layer, not just the serializer. |
| MCP defaults `"agent"`, REST stays `NULL`, additive for every existing client | **Met and proven end to end** through a real authenticated MCP session against the container: MCP-omitted ⇒ `agent`, MCP-explicit ⇒ `human`, REST-explicit ⇒ `human`, REST-omitted ⇒ `NULL`; the marker survives the hand-written Redis round-trip; the unfiltered read still returns the `NULL` row. |
| Publicly documented for third-party adoption | **Met.** SKILL.md (byte-parity gate green), README, and `docs/cli.md` all carry the contract, plus the honest key-scope statement D4 item 3 asked for. |
| Ordering: land before the downstream consumer | **Met** — nothing here depends on the consumer, and the contract is additive. |

**Scope discipline held.** No dashboard visual control was invented, no backfill, no sentiment enum,
no changple-side work, no deployment. The two assertion edits in the phase (`test_admin_api`'s single
full-record exact dict, `skill-preview-ssr`'s last-heading probe) are both mirrors of an artifact
rather than client contracts, both were the *only* such assertion in the tree, and both were argued
rather than waved through. The one deviation I'd have questioned — S1 editing
`test_org_credentials_migration_round_trip` — is a revision anchor, not an assertion change, and it
fixed a latent trap that would have broken the next migration in *any* phase.

**Doc impact list completeness.** I re-derived the phase's real changes from `git diff d8efbf3..HEAD`
outside `works/` and checked them against the list. S4's sweep is sound; I found no durable-truth
change without a line. The only thing I'd add is the local-compose MCP env gap, which S3 recorded in
its notes and which the `security.md` / `operations.md` lines already carry — so it is covered.

## 4. Doc consolidation (pass-only; P14 is **not** in parallel mode)

Eleven versions, one per affected doc, each consolidating **all** of that doc's P14 notes:

| Doc | New version | Carries |
|---|---|---|
| `api` | `v0010` | A new **Shared Capture Provenance Rules** contract (values, the per-transport default, the field-mapping convention, the `q`-only-on-`/app/feedback` caveat), `recorded_by` on the REST capture inputs, on the MCP tool inputs, on all four list filters, in the record shape, and in the PATCH-immutable list |
| `data` | `v0005` | The new column + index + migration head, no-`CHECK`/no-backfill rationale, live-verified reversibility, deployment ordering, and the **pin-downgrade-targets-by-revision-id** rule with its 50-failure cautionary tale |
| `architecture` | `v0012` | `recorded_by` in the `feedback_events` shape + index list, why it is its own column and not a `trigger_type` value, the MCP flat-parameter and MCP-only-default properties, and the queue serializer as the silent-loss trap |
| `decisions` | `v0008` | **D-P14-1** (the marker design + every rejected alternative), **D-P14-2** (the per-transport defaults), **D-P14-3** (the field mapping, documented-not-enforced `comment`, and the deliberate absence of a CLI marker flag) |
| `backend` | `v0007` | The new `src/vocky/recorded_by.py` module, the `normalize_mcp_payload` default seam, the delegating read-side filter validator, the load-bearing `None` default on the record, field-position convention, and the two-duplicate-pairs warning |
| `security` | `v0011` | A new **Third-Party Agent Runtimes Hold Unscoped Keys** section (D-P3-2 re-raised, mint project-bound, no capture rate limiting and why per-IP is wrong), plus the live-verified `/mcp` `Host` allowlist with the `421`-not-`401` correction |
| `operations` | `v0008` | Prod rollout ordering as the worked example of an additive migration needing zero operational change, the live `421` verification, and the local-compose env-forwarding gap |
| `qa` | `v0004` | Updated suite counts (238), `vocky-smoke` as the deploy-time capture-field guard, the two artifact-mirroring assertions that bite on every change, and live-MCP as a manual-only check (rebuild images; probe `/mcp/` with redirects off) |
| `frontend` | `v0009` | `recorded_by` as URL-driven filter only + the detail row, why no rendered control exists, and the prettier reflow on `toQuery` |
| `experience` | `v0013` | The full public agent-capture contract: the field-mapping table, the marker and its one inferring transport, key scope stated plainly, an updated MCP payload example, the read-side filter, and the skill's 7→8-step growth |
| `product` | `v0012` | A new **Agent-recorded feedback (P14)** section, `recorded_by` in the field taxonomy, and the skill's expanded published contents |

Method: `doc-new-version --source P14.REVIEW` per doc → edited only the returned `edit_path` →
`rebuild-docs` → `validate`. **No `docs/current/*.md` file was hand-edited**; all eleven are
regenerated. `git status` confirms the only non-`works/` changes are `docs/`.

**Two consolidation notes worth carrying forward** (also in `phase.md`):

1. **Keep review `--summary` strings short.** `doc-new-version` slugifies the entire summary into the
   filename; a long one produced a path that broke the 255-byte name limit *once an editor appended a
   temp suffix* (`ENAMETOOLONG`), after the version file and its index entry already existed.
   Recovery was manual: delete the file, drop its `docs/index.json` entry, restore `latest`,
   `rebuild-docs`. The rerun with a shorter summary was clean.
2. **A pre-existing artifact was cleaned up.** Every `api.md` version since `v0002` (the P1 era) ended
   with stray `</content>` / `</invoke>` lines — a leaked tool-call closing tag that
   `doc-new-version`'s base-body carry had propagated forward for eight versions. `v0010` drops them.
   No other doc carries the artifact. This is the only content I removed rather than added.

## 5. For the operator — one open question, deliberately not decided

**Should `comment` be server-enforced when `recorded_by == "agent"`?** P14 chose documentation over
enforcement (D-P14-3), and I agree that was right *for this phase*: a global requirement would `400`
every existing REST/CLI/MCP client that omits `comment`, breaking the additivity bar the whole phase
was built on. But it means an agent can record a bare sentiment with no note and vocky will accept it
— the quality bar lives in the published skill, not the schema. If you want it enforced, the only
defensible shape is **"required *when* `recorded_by == "agent"`"**, which is a small conditional-
validation slice in a later phase. **This is your call, not mine.**

Two smaller items, informational:

- **D9 / D10 are filed** (per-credential rate limiting; capture-only key scopes). The rate-limiting one
  is the sharper of the two now that the capture surfaces are publicly documented for third parties.
- **Local `docker-compose.yml` does not forward `VOCKY_MCP_ALLOWED_HOSTS`/`_ORIGINS` to `app`**, so
  `/mcp` over a local stack's external hostname `421`s. Production is unaffected. It is recorded in
  `operations.md` and `security.md` but nobody has filed it as a deferred job — you may want to.

## 6. Deviations from `plan.md`

- **`make smoke` was run rather than skipped** — the plan allowed skipping if the stack were down; it
  was up and healthy, so the live check ran and passed.
- **One over-long `doc-new-version` summary had to be rolled back and re-created** (see §4 note 1).
  The rollback was surgical and verified: after `rebuild-docs`, the only `docs/index.json` diff was
  the `last_rebuilt_at` timestamp.
- **The stray `</content>` / `</invoke>` lines were removed from the new `api.md` version.** The plan
  said "consolidate faithfully — don't invent beyond the notes + the tree"; dropping a leaked tool-call
  tag is a correction to the doc I was authoring, not new content, and leaving it would have carried a
  visible defect into a ninth version.

No other deviations. No source code was edited, no commit was made, and no workflow state transition
was run — `review-phase` and `finish-slice` are the orchestrator's.
