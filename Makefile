ENV_FILE ?= .env

ifneq ("$(wildcard $(ENV_FILE))","")
include $(ENV_FILE)
endif

VOCKY_PORT ?= 8000
VOCKY_PUBLISH_HOST ?= 127.0.0.1
POSTGRES_PUBLISH_HOST ?= 127.0.0.1
REDIS_PUBLISH_HOST ?= 127.0.0.1
VOCKY_BASE_URL ?= http://127.0.0.1:$(VOCKY_PORT)
VOCKY_EXTERNAL_BASE_URL ?=
WAIT_READY_TIMEOUT ?= 60

EXPORTED_ENV_VARS := DATABASE_URL REDIS_URL TEST_DATABASE_URL VOCKY_HOST VOCKY_PORT VOCKY_LOG_LEVEL VOCKY_HTTP_USER_AGENT VOCKY_MCP_ALLOWED_HOSTS VOCKY_MCP_ALLOWED_ORIGINS VOCKY_MCP_AUTH_TOKEN VOCKY_API_AUTH_TOKEN VOCKY_ADMIN_AUTH_TOKEN VOCKY_BASE_URL VOCKY_EXTERNAL_BASE_URL VOCKY_PUBLISH_HOST POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD POSTGRES_PORT POSTGRES_PUBLISH_HOST REDIS_PORT REDIS_PUBLISH_HOST WAIT_READY_TIMEOUT
export $(EXPORTED_ENV_VARS)

.PHONY: sync test package-check compose-up compose-down compose-logs migrate wait-ready smoke-run smoke bootstrap verify check-test-db require-external-base-url external-smoke external-verify

sync:
	uv sync

check-test-db:
	@test -n "$(DATABASE_URL)" || { echo "DATABASE_URL must be set. Copy .env.example to .env first."; exit 1; }
	@test -n "$(TEST_DATABASE_URL)" || { echo "TEST_DATABASE_URL must be set. Copy .env.example to .env first."; exit 1; }
	@test "$(DATABASE_URL)" != "$(TEST_DATABASE_URL)" || { echo "TEST_DATABASE_URL must point at a separate disposable database."; exit 1; }

test: check-test-db
	uv run pytest

package-check:
	@tmp_dir=$$(mktemp -d); \
	trap 'rm -rf "$$tmp_dir"' EXIT; \
	uv build --wheel --out-dir "$$tmp_dir"; \
	wheel=$$(find "$$tmp_dir" -maxdepth 1 -name 'vocky-*.whl' -print -quit); \
	test -n "$$wheel" || { echo "package-check did not build a wheel"; exit 1; }; \
	uv run python scripts/check_admin_ui_package.py "$$wheel"

compose-up:
	docker compose up --build -d redis postgres app worker

compose-down:
	docker compose down --remove-orphans

compose-logs:
	docker compose logs -f redis postgres app worker

migrate:
	uv run alembic upgrade head

wait-ready:
	uv run python scripts/wait_for_health.py

smoke-run:
	uv run vocky-smoke

smoke: wait-ready
	$(MAKE) smoke-run

bootstrap: sync compose-up migrate wait-ready

verify: package-check smoke test

require-external-base-url:
	@test -n "$(VOCKY_EXTERNAL_BASE_URL)" || { echo "VOCKY_EXTERNAL_BASE_URL must be set for external access checks."; exit 1; }

external-smoke: require-external-base-url
	$(MAKE) smoke-run VOCKY_BASE_URL="$(VOCKY_EXTERNAL_BASE_URL)"

external-verify: require-external-base-url
	$(MAKE) wait-ready VOCKY_BASE_URL="$(VOCKY_EXTERNAL_BASE_URL)"
	$(MAKE) smoke-run VOCKY_BASE_URL="$(VOCKY_EXTERNAL_BASE_URL)"
