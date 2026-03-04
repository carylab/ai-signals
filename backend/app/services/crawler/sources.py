"""
Sources registry — runtime helpers for working with NewsSource records.

Provides:
  - load_active_sources()   : load all active sources from DB
  - get_source_by_slug()    : lookup single source
  - mark_source_error()     : update health counters after a fetch failure
  - SourceHealthChecker     : async context manager used by CollectStage
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.source import NewsSource

logger = structlog.get_logger(__name__)


async def load_active_sources(session: AsyncSession) -> list[NewsSource]:
    """Return all active sources ordered by priority (1 = highest)."""
    result = await session.execute(
        select(NewsSource)
        .where(NewsSource.is_active.is_(True))
        .order_by(NewsSource.priority.asc())
    )
    sources = list(result.scalars().all())
    logger.info("sources_loaded", count=len(sources))
    return sources


async def get_source_by_slug(
    session: AsyncSession, slug: str
) -> Optional[NewsSource]:
    return await session.scalar(
        select(NewsSource).where(NewsSource.slug == slug)
    )


async def mark_source_error(
    session: AsyncSession,
    source: NewsSource,
    error: str,
    *,
    disable_after: int = 10,
) -> None:
    """
    Record a fetch failure on a source.
    Disables the source automatically after `disable_after` consecutive errors.
    """
    source.consecutive_errors += 1
    source.last_error = error[:500]

    if source.consecutive_errors >= disable_after:
        source.is_active = False
        logger.warning(
            "source_auto_disabled",
            slug=source.slug,
            consecutive_errors=source.consecutive_errors,
        )
    await session.flush()


async def mark_source_ok(
    session: AsyncSession,
    source: NewsSource,
    articles_fetched: int,
) -> None:
    """Record a successful fetch — reset error counters."""
    source.consecutive_errors = 0
    source.last_error = None
    source.last_fetched_at = datetime.now(timezone.utc).isoformat()
    source.total_articles_fetched += articles_fetched
    await session.flush()


class SourceHealthChecker:
    """
    Async context manager that wraps a source fetch and automatically
    records success or failure in the DB.

    Usage:
        async with SourceHealthChecker(session, source) as checker:
            articles = await rss.fetch(source)
            checker.set_count(len(articles))
    """

    def __init__(self, session: AsyncSession, source: NewsSource) -> None:
        self._session = session
        self._source = source
        self._count = 0
        self._error: Optional[str] = None

    def set_count(self, n: int) -> None:
        self._count = n

    def set_error(self, error: str) -> None:
        self._error = error

    async def __aenter__(self) -> "SourceHealthChecker":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        if exc_type is not None:
            self._error = str(exc_val)

        if self._error:
            await mark_source_error(self._session, self._source, self._error)
        else:
            await mark_source_ok(self._session, self._source, self._count)

        # Do not suppress exceptions
        return False
