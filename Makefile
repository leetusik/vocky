APP_BASE_URL ?= http://127.0.0.1:8000

.PHONY: sync test compose-up compose-down compose-logs migrate smoke

sync:
	uv sync

test:
	uv run pytest

compose-up:
	docker compose up --build -d postgres app

compose-down:
	docker compose down --remove-orphans

compose-logs:
	docker compose logs -f postgres app

migrate:
	uv run alembic upgrade head

smoke:
	VOCKY_BASE_URL=$(APP_BASE_URL) uv run vocky-smoke
