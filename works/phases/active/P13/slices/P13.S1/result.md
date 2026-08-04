# Result — P13.S1: owner-email recipient resolution (accounts repository + service)

## What landed

1. **`src/vocky/accounts/repository.py`** — `AccountsRepository.get_owner_email_for_project(project_id: UUID) -> str | None`, inserted in the "projects" section right after `get_project_by_name` (its house-style neighbor for the oldest-wins tie-break pattern).
   - One `select(UserModel.email)` joined `TenantMemberModel.user_id == UserModel.id` then `ProjectModel.tenant_id == TenantMemberModel.tenant_id`, filtered `ProjectModel.id == project_id` and `TenantMemberModel.role == "owner"`.
   - `.order_by(TenantMemberModel.created_at, TenantMemberModel.id).limit(1)` + `.scalars().first()` — never `.one()` / `scalar_one_or_none()`, mirroring `get_project_by_name`.
   - Docstring states the multi-tenant guarantee (project-anchored join can't leak across tenants) and the oldest-wins tie-break rationale.
   - `role="owner"` kept as the same bare string literal used at `service.py:125` and `:165` (now `:135`/`:175` after the insertion shifted line numbers) — no shared constant introduced, no write-site changes.
   - Selecting the single column (`UserModel.email`) directly returns `str | None` from `.scalars().first()`, so no `_to_*_record` mapper was needed — matches the declared return type with no new `*Record`.

2. **`src/vocky/accounts/service.py`** — `AccountsService.get_owner_email_for_project(project_id: UUID) -> str | None`, inserted right before `get_or_create_project`. Thin passthrough: `async with self._session_maker() as session:` → `AccountsRepository(session).get_owner_email_for_project(project_id)`, `SQLAlchemyError` → rollback + `AccountsReadError`, same shape as every other read method in the file (e.g. `get_project_by_name`). No transaction, no new type.

3. **`tests/test_accounts_persistence.py`** — three new DB-backed tests, placed just before `test_credential_lifecycle_active_lookup_and_revoke` (grouped with the other project-flavored tests):
   - `test_get_owner_email_for_project_resolves_owner` — `create_user` + `create_tenant_with_owner` + `create_project` → the owner's email resolves.
   - `test_get_owner_email_for_project_unknown_project_is_none` — a random `uuid4()` project id → `None`.
   - `test_get_owner_email_for_project_picks_oldest_owner` — a tenant with two `role="owner"` rows (the first from `create_tenant_with_owner`, the second inserted directly via `AccountsRepository.add_tenant_member` through a raw `get_session_maker()` session + commit, since `AccountsService` exposes no public "add another member" method) → the older member's email wins.
   Added imports: `from uuid import uuid4` and `from vocky.accounts.repository import AccountsRepository`.

## Validation

- `uv run pytest tests/test_accounts_persistence.py -q` → **10 passed** (7 pre-existing + 3 new). DB reachable at `postgresql+psycopg://vocky:vocky@127.0.0.1:55432/vocky_test` (dev compose stack was already up: `vocky-postgres-1` healthy).
- Ruff: **not applicable** — checked `pyproject.toml` (no `[tool.ruff]` section, `ruff` not in `dependencies`/`dev` group) and `Makefile` (no lint target); `uv run ruff --version` fails with "Failed to spawn: `ruff`: No such file or directory". The plan's ruff step was conditional ("if ruff is the configured linter") — it is not configured in this repo, so it was skipped rather than run against a tool that isn't installed.
- Additionally ran `uv run pytest -q` (full suite, not required by the plan but cheap given the live DB and the multi-tenant-correctness stakes) → **218 passed**, confirming no regressions elsewhere.

## Deviations from plan.md

- None in substance. One clarification: the plan's ruff validation step was conditional on ruff being the configured linter; it is not (no `ruff` dependency, no config, no lint target), so that step was a documented no-op rather than a deviation.
- Test 3's "two owner rows" setup used `AccountsRepository.add_tenant_member` directly (via a fresh session from `get_session_maker()`) rather than a second `AccountsService` call, because the service has no public method to add an additional member to an existing tenant (`create_tenant_with_owner` and `provision_signup` both create a *new* tenant). This matches the plan's own "or repo-level equivalents" allowance.

## For P13.S2 (notifier)

- Call `AccountsService.get_owner_email_for_project(project_id: UUID) -> str | None` (already exported via the existing `get_accounts_service()` factory — no new export needed). Returns `None` when the project doesn't exist or the tenant has no owner; the notifier should treat that as "nothing to notify" (no exception raised on the "not found" path — only `AccountsReadError` on a genuine DB failure, which callers should still guard against per S3's containment rule).
