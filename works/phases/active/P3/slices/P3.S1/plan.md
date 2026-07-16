# P3.S1 — Project-scope foundation (native plan → slice-executor-mid)

Read `works/phases/active/P3/phase.md` (Findings & Notes, D-P3-1…6, anchors) and `AGENTS.md` first.
This is the **foundation slice** of P3 — S2/S3/S4 depend on it. Implement exactly the changes below,
following the cited precedents. **No new endpoints.** Write no commits and make no status
transitions; the orchestrator owns those. Keep tests terse.

## A. Migration + model — `feedback_events.project_id`

- **Migration** `alembic/versions/20260716_<hhmm>_add_feedback_project_id.py`, chained
  `down_revision = "20260715_1200"` (current head). Follow the shape of
  `alembic/versions/20260424_1633_add_action_feedback_fields.py`:
  - `op.add_column("feedback_events", sa.Column("project_id", sa.UUID(), nullable=True))`
  - `op.create_foreign_key("fk_feedback_events_project_id_projects", "feedback_events", "projects",
    ["project_id"], ["id"], ondelete="CASCADE")` — **net-new pattern** (no `create_foreign_key`
    precedent in the repo; the FK-constraint *naming* matches `20260715_1200`). CASCADE follows the
    schema convention (all FKs cascade; there is no project-delete endpoint yet).
  - `op.create_index("ix_feedback_events_project_id", "feedback_events", ["project_id"])`
  - `downgrade()`: drop index → `op.drop_constraint("fk_feedback_events_project_id_projects",
    "feedback_events", type_="foreignkey")` → drop column.
- **Model** `src/vocky/persistence/models.py` (`FeedbackEventModel`, 22-98): add
  `project_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True),
  ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)` (both `ForeignKey` and `PG_UUID`
  imports already present) and `Index("ix_feedback_events_project_id", "project_id")` in
  `__table_args__`. The naming convention auto-derives the FK name to match the migration.

## B. Scope-threading + best-effort `last_used_at` stamping

- **`src/vocky/auth.py` `ProjectCredentialAuthMiddleware.__call__` (98-122):** after the credential
  resolves non-None: (1) stash it on a **dedicated namespaced scope key** —
  `scope["vocky.project_credential"] = credential` (the `ProjectCredentialRecord` carries `.id` and
  `.project_id`); (2) **best-effort** stamp `await get_accounts_service()
  .touch_credential_last_used(credential.id)` inside `try/except AccountsPersistenceError` → log and
  continue (a stamping failure must never turn a valid ingest into a 500). Update the class docstring
  (drop the "identity-only … P3" note). Add a small accessor
  `get_request_credential(request) -> ProjectCredentialRecord` reading
  `request.scope["vocky.project_credential"]` for handlers.
  - *Use the custom scope key, not `request.state`*: the middleware sits inside Starlette's stack, so
    a namespaced scope key is immune to any Starlette `scope["state"]` (re)initialization.
  - You'll need to import `AccountsPersistenceError` (from `vocky.accounts.service`) and a module logger.
- **`src/vocky/accounts/auth.py` `require_user` (57-81):** after `auth_token` resolves, best-effort
  `await service.touch_auth_token_last_used(sha256_hex(token))` (the hash is already in hand; the repo
  method keys by `token_hash`) inside `try/except AccountsPersistenceError` → log, don't fail auth.
  Update the module docstring (drop the "never touches last_used_at … P3" line).
- Stamp **always** (one indexed UPDATE by PK). Do **not** implement a throttle (note it as a future
  optimization only if you touch the docstring).

## C. Thread `project_id` through capture (worker unchanged)

- **`src/vocky/feedback/types.py`:** `CreateFeedbackEvent` gains `project_id: UUID | None = None`;
  `FeedbackEventRecord` gains `project_id: UUID | None`.
- **`src/vocky/feedback/repository.py`:** `create_feedback_event` (48-81) passes
  `project_id=payload.project_id` into `FeedbackEventModel(...)`; `_to_record` (569+) maps
  `project_id=model.project_id`.
- **`src/vocky/capture_queue.py`:** `_serialize_payload` (56-87) adds
  `"project_id": str(payload.project_id) if payload.project_id is not None else None`;
  `_deserialize_payload` (90-175) adds
  `project_id=UUID(str(raw["project_id"])) if raw.get("project_id") is not None else None`.
- **`src/vocky/api.py` `capture_feedback` (89-108):** read the credential via
  `get_request_credential(request)` and set `normalized.payload.project_id = credential.project_id`
  before `enqueue_feedback`. The worker (`worker.py`) needs **no change**.
- Attachments need no `project_id` in S1 (they link to a feedback row that carries it; their credential
  `last_used_at` is already stamped by the middleware since upload/download are `/api/*`).

## D. Read-model project filter + tighten the end-user self-read (D-P3-6)

- **`src/vocky/feedback/types.py`:** `FeedbackQueryFilters` gains `project_id: UUID | None = None`.
- **`src/vocky/feedback/repository.py` `_apply_query_filters` (525-567):** add
  `if filters.project_id is not None: statement = statement.where(FeedbackEventModel.project_id ==
  filters.project_id)`. This is the shared hook S2/S3 will reuse — keep it clean.
- **`src/vocky/api.py` `list_user_feedback` (217-253):** inject the credential's project into the
  query — set `filters.project_id = get_request_credential(request).project_id`. The self-read is now
  scoped by `user_id` + `source_product` **and** the credential's project. Legacy rows
  (`project_id IS NULL`) fall out of the scoped read — acceptable pre-MVP.

## E. Tests (terse — high-value only)

- **`tests/test_persistence.py` (45-59):** bump the head-pin to the new revision id; insert
  `"ix_feedback_events_project_id"` into the sorted index list (between `…_ingested_at` and `…_session_id`).
- Extend existing suites (no new sprawl), reusing the `configured_project_credential` fixture +
  `httpx.ASGITransport` + `fakeredis`:
  - `tests/test_capture_api.py`: a captured event persists the authenticating credential's `project_id`.
  - `tests/test_user_feedback_api.py`: the self-read is project-scoped (a project-A credential cannot
    read a project-B row that shares `user_id`/`source_product`).
  - A small stamping check: a `/api/*` call sets the credential's `last_used_at`; `require_user`
    (or an `/app/*` call) sets the auth-token's `last_used_at`.

## Verify before returning

- `uv run alembic upgrade head`, then `uv run alembic downgrade -1` and back up (prove reversibility).
- `uv run pytest tests/test_persistence.py tests/test_capture_api.py tests/test_user_feedback_api.py`
  (real Postgres per `conftest.py`; ensure the test DB is available — if it is not, say so and return
  `blocked` rather than skipping validation).
- Optionally a broader `uv run pytest` if quick.

## Write result.md + phase.md notes; return a verdict

- Write a free-form `result.md` summarizing what changed and the verification output.
- Append cross-slice notes to `phase.md`: the **final migration revision id** (S2/S3 chain onto it),
  the scope-key name `vocky.project_credential` + the `get_request_credential` accessor (S2 reuses),
  the `FeedbackQueryFilters.project_id` hook (S2/S3 reuse), and one **Doc impact** line under the
  existing `## Doc impact` list (`data.md`: `feedback_events.project_id` + new migration; `security.md`:
  the self-read is now project-scoped). Do **not** run `doc-new-version`.
- Return `done` if all verification passes; `blocked` if the test DB/migration cannot run; `escalate`
  with findings if the slice exceeds a mid-tier mechanical scope. No commits, no status transitions.
