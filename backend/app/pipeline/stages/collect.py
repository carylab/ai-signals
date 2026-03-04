"""
Stage: collect

Fetches raw articles from all active NewsSource records.
Uses RSS fetcher as primary; falls back to web scraper.
Runs sources concurrently with a semaphore to respect rate limits.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone, timedelta
from typing import TYPE_CHECKING

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.pipeline.base import PipelineContext, PipelineStageBase
from app.models.source import NewsSource, SourceType

if TYPE_CHECKING:
    pass

logger = structlog.get_logger(__name__)

# Max concurrent source fetches
_CONCURRENCY = 8


class CollectStage(PipelineStageBase):
    name = "collect"

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def process(self, ctx: PipelineContext) -> PipelineContext:
        # Import here to avoid circular imports at module load
        from app.services.crawler.rss_fetcher import RSSFetcher
        from app.services.crawler.web_scraper import WebScraper

        rss = RSSFetcher()
        scraper = WebScraper()

        # Load active sources
        result = await self._session.execute(
            select(NewsSource).where(NewsSource.is_active.is_(True))
        )
        sources: list[NewsSource] = list(result.scalars().all())

        ctx.set_stage_stat(self.name, "sources_total", len(sources))
        logger.info("collect_sources_loaded", count=len(sources))

        sem = asyncio.Semaphore(_CONCURRENCY)
        tasks = [
            self._fetch_source(source, rss, scraper, sem, ctx)
            for source in sources
        ]
        results = await asyncio.gather(*tasks, return_exceptions=False)

        all_articles: list[dict] = []
        for batch in results:
            all_articles.extend(batch)

        ctx.raw_articles = all_articles
        ctx.articles = list(all_articles)  # working copy

        ctx.set_stage_stat(self.name, "articles_fetched", len(all_articles))
        return ctx

    async def _fetch_source(
        self,
        source: NewsSource,
        rss: "RSSFetcher",
        scraper: "WebScraper",
        sem: asyncio.Semaphore,
        ctx: PipelineContext,
    ) -> list[dict]:
        async with sem:
            try:
                if source.feed_url and source.source_type == SourceType.RSS:
                    articles = await rss.fetch(source)
                else:
                    articles = await scraper.fetch(source)

                # Update source health
                now_iso = datetime.now(timezone.utc).isoformat()
                source.last_fetched_at = now_iso
                source.consecutive_errors = 0
                source.total_articles_fetched += len(articles)

                ctx.increment_stat(self.name, "sources_ok")
                return articles

            except Exception as exc:
                source.consecutive_errors += 1
                source.last_error = str(exc)

                # Disable source after 10 consecutive failures
                if source.consecutive_errors >= 10:
                    source.is_active = False
                    logger.warning(
                        "source_disabled",
                        slug=source.slug,
                        consecutive_errors=source.consecutive_errors,
                    )

                ctx.add_error(self.name, f"source={source.slug}: {exc}")
                ctx.increment_stat(self.name, "sources_error")
                return []
