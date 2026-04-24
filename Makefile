ENV_FILE ?= .env

ifneq ("$(wildcard $(ENV_FILE))","")
include $(ENV_FILE)
endif

VOCKY_PORT ?= 8000
ifneq ($(strip $(APP_BASE_URL)),)
VOCKY_BASE_URL ?= $(APP_BASE_URL)
endif
VOCKY_BASE_URL ?= http://127.0.0.1:$(VOCKY_PORT)
WAIT_READY_TIMEOUT ?= 60

EXPORTED_ENV_VARS := DATABASE_URL TEST_DATABASE_URL VOCKY_HOST VOCKY_PORT VOCKY_LOG_LEVEL VOCKY_BASE_URL POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD POSTGRES_PORT WAIT_READY_TIMEOUT
export $(EXPORTED_ENV_VARS)

.PHONY: sync test compose-up compose-down compose-logs migrate smoke wait-ready bootstrap verify check-test-db

sync:
	uv sync

check-test-db:
	@test -n "$(DATABASE_URL)" || { echo "DATABASE_URL must be set. Copy .env.example to .env first."; exit 1; }
	@test -n "$(TEST_DATABASE_URL)" || { echo "TEST_DATABASE_URL must be set. Copy .env.example to .env first."; exit 1; }
	@test "$(DATABASE_URL)" != "$(TEST_DATABASE_URL)" || { echo "TEST_DATABASE_URL must point at a separate disposable database."; exit 1; }

test: check-test-db
	uv run pytest

compose-up:
	docker compose up --build -d postgres app

compose-down:
	docker compose down --remove-orphans

compose-logs:
	docker compose logs -f postgres app

migrate:
	uv run alembic upgrade head

wait-ready:
	uv run python scripts/wait_for_health.py

smoke: wait-ready
	uv run vocky-smoke

bootstrap: sync compose-up migrate

verify: smoke test
