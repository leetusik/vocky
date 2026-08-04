# Plan — P13.S1: owner-email recipient resolution (accounts repository + service)

## Context

Phase P13 sends one plain-text email per persisted feedback event to the owning org's owner. This
slice lands the missing data primitive: given a `project_id`, resolve the owner's account email by
walking `projects.tenant_id → tenant_members(role='owner') → users.email`. It lands with no caller —
P13.S2 (the notifier) consumes it. Read `works/phases/active/P13/phase.md` first, especially
"Codebase facts (verified at DECOMP)".

This is the phase's multi-tenant correctness hot spot: a wrong join or missing `role='owner'` filter
mails one org's feedback to another org's owner. Get the joins and the tie-break exactly right.

## Changes

1. **`src/vocky/accounts/repository.py`** — add one read method to `AccountsRepository`:

   ```
   async def get_owner_email_for_project(self, project_id: UUID) -> str | None
   ```

   - Single SELECT: `UserModel.email` joined `TenantMemberModel.user_id == UserModel.id`, joined
     `ProjectModel.tenant_id == TenantMemberModel.tenant_id`, filtered
     `ProjectModel.id == project_id` and `TenantMemberModel.role == "owner"`.
   - **Deterministic oldest-wins tie-break**: nothing forbids two `role='owner'` rows per tenant, so
     `.order_by(TenantMemberModel.created_at, TenantMemberModel.id).limit(1)` and `.first()` — never
     `.one()` / `scalar_one_or_none()` (mirrors `get_project_by_name`'s documented pattern,
     repository.py:143-168).
   - Returns `None` when the project doesn't exist or the tenant has no owner member.
   - Docstring should state the multi-tenant guarantee and the tie-break, in the house style of the
     neighbors.
   - `role="owner"` stays a bare string literal matching the two write sites in
     `accounts/service.py` (lines ~125, ~165). Do NOT refactor the write sites.

2. **`src/vocky/accounts/service.py`** — thin passthrough on `AccountsService`:

   ```
   async def get_owner_email_for_project(self, project_id: UUID) -> str | None
   ```

   `async with self._session_maker() as session:` then delegate to the repository — same shape as
   the other read methods (e.g. the unscoped read around service.py:363-368). No transaction needed
   (read-only). No type changes — the return is a plain `str | None`, no new `*Record`.

## Tests (small — extend `tests/test_accounts_persistence.py` in place)

DB-backed, using the existing `configured_database` fixture and house style. Three cases:

1. Happy path: `create_tenant_with_owner` (or repo-level equivalents) + a project → resolves the
   owner's email.
2. Unknown `project_id` (random UUID) → `None`.
3. Two owner rows in one tenant → the **older** member's email wins (insert two owners with
   distinct users; assert the first-added one is returned).

No new fixtures, no scaffolding sprawl. Note: these tests need the live test Postgres
(`TEST_DATABASE_URL`, conftest default `postgresql+psycopg://vocky:vocky@127.0.0.1:55432/vocky`) —
if the DB is unreachable, report that honestly rather than pretending the suite passed.

## Validation

- `uv run pytest tests/test_accounts_persistence.py -q` (needs the test DB; `make test` also works
  but runs everything).
- `uv run ruff check src/vocky/accounts tests/test_accounts_persistence.py` and
  `uv run ruff format --check` on the touched files, if ruff is the configured linter (check
  `pyproject.toml` / Makefile for the house lint command and use that).

## Out of scope

- No settings, no notifier, no worker changes (S2/S3).
- No shared `OWNER_ROLE` constant refactor of the write sites.
- No changes to `types.py` records.

## Wrap-up

Write `result.md` in this slice folder; append durable cross-slice notes to `phase.md` (at minimum:
the exact method names S2 should call, and a one-line "Doc impact" note under "Doc impact" —
`backend.md` gains the owner-email primitive).
