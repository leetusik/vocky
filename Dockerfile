FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY pyproject.toml uv.lock README.md /app/
RUN uv sync --frozen --no-dev --no-install-project

COPY alembic.ini /app/alembic.ini
COPY alembic /app/alembic
COPY src /app/src
RUN uv sync --frozen --no-dev

CMD ["uv", "run", "--no-sync", "vocky-server"]
