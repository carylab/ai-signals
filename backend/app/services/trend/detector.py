"""
Trend detector — orchestrates aggregation, scoring, and DB write-back.

Responsibilities:
  1. Run TrendAggregator to compute TrendResult for every entity
  2. Write TrendSnapshot records for historical tracking
  3. Update trend_score on Tag / Company / AIModel rows (used by API)
  4. Return a summary dict for pipeline stats

Called once per day, typically after the store stage completes.
"""
from __future__ import annotations

from datetime import date
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tag import Tag
from app.models.company import Company, AIModel
from app.models.trend_snapshot import TrendSnapshot, EntityType
from app.services.trend.aggregator import TrendAggregator
from app.services.trend.calculator import TrendResult

logger = structlog.get_logger(__name__)


class TrendDetector:
    """
    Main entry point for the daily trend detection run.

    Usage:
        detector = TrendDetector(session)
        summary = await detector.run(target_date="2026-03-04")
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._aggregator = TrendAggregator(session)

    async def run(self, target_date: str | None = None) -> dict[str, Any]:
        td = target_date or date.today().isoformat()
        logger.info("trend_detection_start", date=td)

        # 1. Compute scores
        results = await self._aggregator.aggregate_all(td)

        # 2. Persist snapshots + update entity rows
        counts: dict[str, int] = {}
        for entity_type, trend_list in results.items():
            await self._write_snapshots(td, trend_list)
            await self._update_entity_scores(entity_type, trend_list)
            counts[entity_type] = len(trend_list)

        await self._session.commit()

        summary = {
            "date": td,
            "tags_updated": counts.get(EntityType.TAG, 0),
            "companies_updated": counts.get(EntityType.COMPANY, 0),
            "models_updated": counts.get(EntityType.AI_MODEL, 0),
            "top_tags": _top_names(results.get(EntityType.TAG, []), 5),
            "top_companies": _top_names(results.get(EntityType.COMPANY, []), 3),
        }
        logger.info("trend_detection_done", **summary)
        return summary

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _write_snapshots(
        self, date_str: str, results: list[TrendResult]
    ) -> None:
        """Upsert one TrendSnapshot per entity."""
        for r in results:
            existing = await self._session.scalar(
                select(TrendSnapshot).where(
                    TrendSnapshot.date == date_str,
                    TrendSnapshot.entity_type == r.entity_type,
                    TrendSnapshot.entity_slug == r.slug,
                )
            )
            if existing:
                snap = existing
            else:
                snap = TrendSnapshot(
                    date=date_str,
                    entity_type=r.entity_type,
                    entity_slug=r.slug,
                    entity_name=r.name,
                )
                self._session.add(snap)

            snap.count_1d = r.count_1d
            snap.count_7d = r.count_7d
            snap.count_30d = r.count_30d
            snap.count_prev_7d = r.count_prev_7d
            snap.avg_importance = r.avg_importance
            snap.velocity = r.velocity
            snap.trend_score = r.trend_score

        await self._session.flush()

    async def _update_entity_scores(
        self, entity_type: str, results: list[TrendResult]
    ) -> None:
        """Write trend_score back to the canonical entity table."""
        slug_to_score = {r.slug: r for r in results}

        if entity_type == EntityType.TAG:
            rows = (await self._session.execute(select(Tag))).scalars().all()
            for tag in rows:
                r = slug_to_score.get(tag.slug)
                if r:
                    tag.trend_score = r.trend_score
                    tag.news_count_7d = r.count_7d
                    tag.news_count_30d = r.count_30d

        elif entity_type == EntityType.COMPANY:
            rows = (await self._session.execute(select(Company))).scalars().all()
            for company in rows:
                r = slug_to_score.get(company.slug)
                if r:
                    company.trend_score = r.trend_score
                    company.news_count_7d = r.count_7d
                    company.news_count_30d = r.count_30d

        elif entity_type == EntityType.AI_MODEL:
            rows = (await self._session.execute(select(AIModel))).scalars().all()
            for model in rows:
                r = slug_to_score.get(model.slug)
                if r:
                    model.trend_score = r.trend_score
                    model.news_count_7d = r.count_7d

        await self._session.flush()


def _top_names(results: list[TrendResult], n: int) -> list[str]:
    return [r.name for r in results[:n]]
