"""CLI entrypoint for running the Vocky service."""

from __future__ import annotations

import uvicorn

from vocky.config import get_settings
from vocky.logging import configure_logging


def main() -> None:
    """Run the Starlette host app."""

    settings = get_settings()
    configure_logging(settings.log_level)
    # Single worker, no `workers=`, no gunicorn. This is load-bearing beyond
    # throughput: `vocky.rate_limit` keeps its per-IP auth throttle state in a
    # plain in-process dict with no cross-process coordination, so it is only
    # correct under one process. Adding `workers=N` here would silently split
    # that state N ways and divide the effective /auth/* rate limit by N.
    uvicorn.run(
        "vocky.app:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
