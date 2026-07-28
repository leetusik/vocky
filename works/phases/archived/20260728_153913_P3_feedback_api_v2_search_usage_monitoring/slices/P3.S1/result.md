# P3.S1 — Project-scope foundation — result

Status: **done**. Implemented exactly as planned (A–E); all validation passes against the real test Postgres. No deviations of substance (one necessary test-fixture edit, noted below).

## What changed

### A. Migration + model — `feedback_events.project_id`
- New migration `alembic/versions/20260716_1500_add_feedback_project_id.py` (**revision `20260716_1500`**, `down_revision = "20260715_1200"`, now head): adds nullable `project_id` (`sa.UUID`), FK `fk_feedback_events_project_id_projects` → `projects.id` (`ondelete=CASCADE`), and index `ix_feedback_events_project_id`. `downgrade()` drops index → FK constraint → column.
- `src/vocky/persistence/models.py`: `FeedbackEventModel` gains the `project_id` mapped column (`PG_UUID`, `ForeignKey("projects.id", ondelete="CASCADE")`, nullable) + `Index("ix_feedback_events_project_id", "project_id")` in `__table_args__`. Naming convention auto-derives the same FK name as the migration.

### B. Scope-threading + best-effort `last_used_at`
- `src/vocky/auth.py`: added module logger + constant `PROJECT_CREDENTIAL_SCOPE_KEY = "vocky.project_credential"`. On a successful `/api/*` auth, `ProjectCredentialAuthMiddleware` stashes the `ProjectCredentialRecord` on `scope["vocky.project_credential"]` and best-effort stamps `touch_credential_last_used(credential.id)` inside `try/except AccountsPersistenceError` (log + continue). New accessor `get_request_credential(request) -> ProjectCredentialRecord`. Docstring updated (dropped the "identity-only … P3" note).
- `src/vocky/accounts/auth.py`: `require_user` best-effort stamps `touch_auth_token_last_used(token_hash)` after the token resolves, inside `try/except AccountsPersistenceError` (log + continue). Added module logger; docstring updated (dropped the "never touches last_used_at … P3" line). No throttle (stamp-always, one indexed UPDATE by PK).

### C. Thread `project_id` through capture (worker unchanged)
- `feedback/types.py`: `CreateFeedbackEvent.project_id: UUID | None = None`; `FeedbackEventRecord.project_id: UUID | None`.
- `feedback/repository.py`: `create_feedback_event` passes `project_id=payload.project_id`; `_to_record` maps `project_id=model.project_id`.
- `capture_queue.py`: `_serialize_payload`/`_deserialize_payload` carry `project_id` across the Redis round trip.
- `api.py::capture_feedback`: sets `normalized.payload.project_id = get_request_credential(request).project_id` before enqueue. `worker.py` untouched.

### D. Read-model project filter + tightened self-read (D-P3-6)
- `feedback/types.py`: `FeedbackQueryFilters.project_id: UUID | None = None`.
- `feedback/repository.py::_apply_query_filters`: adds `project_id` equality predicate (the shared S2/S3 hook).
- `api.py::list_user_feedback`: sets `query.filters.project_id = get_request_credential(request).project_id` (self-read now scoped by `user_id` + `source_product` + credential's project; legacy NULL-project rows fall out). Docstring updated.

### E. Tests
- `tests/test_persistence.py`: head-pin → `20260716_1500`; inserted `ix_feedback_events_project_id` into the sorted index list.
- `tests/test_capture_api.py`: new `test_capture_stamps_authenticating_project_id_and_last_used` — captured payload carries the credential's `project_id` (survives serialize→deserialize) and the credential's `last_used_at` is stamped.
- `tests/test_user_feedback_api.py`: new `test_user_feedback_is_scoped_to_credential_project` — a project-A credential cannot read a project-B row sharing `user_id`/`source_product`. `_seed_feedback` gained an optional `project_id`; the existing list-read tests' caller-scope rows now pass `project_id=str(configured_project_credential.project_id)` (see deviation note).
- `tests/test_app_api.py`: new `test_authed_app_call_stamps_auth_token_last_used` — an authed `/app/tenant` call stamps the auth token's `last_used_at` (None before require_user runs).

## Validation

| Command | Result |
| --- | --- |
| `uv run alembic upgrade head` (dev DB, from `20260715_1200`) | PASS → `20260716_1500 (head)` |
| `uv run alembic downgrade -1` then verify column/index/FK absent | PASS (all three gone) |
| `uv run alembic upgrade head` again then verify column/index/FK present | PASS (all three back) — reversibility proven |
| `uv run pytest tests/test_persistence.py tests/test_capture_api.py tests/test_user_feedback_api.py` | PASS |
| `uv run pytest tests/test_app_api.py` (added auth-token stamping test) | PASS |
| `uv run pytest` (full suite — stamping now runs across all authed tests) | **156 passed** |

Test Postgres reachable at `127.0.0.1:55432` (`vocky_test` via `conftest`); dev DB `vocky` left at head after the reversibility check.

## Deviations from plan

- **Test-fixture edit (necessary, within plan intent):** tightening the self-read to the credential's project meant the existing `tests/test_user_feedback_api.py` list-read tests — which seed rows with a NULL `project_id` — would otherwise return zero rows and fail. As the plan's own step E implies ("reusing the `configured_project_credential` fixture" for the project-scoped read), I added an optional `project_id` param to `_seed_feedback` and stamped the caller-scope rows in the five list-read tests with `configured_project_credential.project_id`. The attachment-**download** tests were left untouched (that route is not project-scoped in S1). No production behavior changed beyond the plan.

## Doc impact (recorded in phase.md — not versioned here)

- `data.md`: `feedback_events.project_id` FK + `ix_feedback_events_project_id` + migration `20260716_1500`.
- `security.md` / `architecture.md`: ingest middleware threads the per-project credential onto the ASGI scope and best-effort stamps `last_used_at`; `GET /api/feedback` self-read is now project-scoped (D-P3-6).

No `doc-new-version` run (per contract, that is the phase REVIEW's job).
