"""CLI entrypoint for running the Vocky service."""

from __future__ import annotations

import uvicorn

from vocky.config import get_settings
from vocky.logging import configure_logging


def main() -> None:
    """Run the Starlette host app."""

    settings = get_settings()
    configure_logging(settings.log_level)
    uvicorn.run(
        "vocky.app:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
