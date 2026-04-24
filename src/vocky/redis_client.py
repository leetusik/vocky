"""Shared Redis client helpers."""

from __future__ import annotations

from redis.asyncio import Redis

from vocky.config import get_settings

_redis_client: Redis | None = None


def get_redis_client() -> Redis:
    """Return the shared async Redis client."""

    global _redis_client

    if _redis_client is None:
        _redis_client = Redis.from_url(
            get_settings().redis_url,
            decode_responses=True,
        )

    return _redis_client


async def dispose_redis_client() -> None:
    """Dispose the cached Redis client during shutdown."""

    global _redis_client

    if _redis_client is not None:
        await _redis_client.aclose()

    _redis_client = None
