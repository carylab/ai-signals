"""
Trend aggregator — queries the database to build EntityCounts
for all tags, companies, and AI models, then delegates scoring
to the calculator.

This module is the bridge between raw DB data and trend scores.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Sequence

import structlog
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.news import NewsArticle, article_tags, article_companies, article_models
from app.models.tag import Tag
from app.models.company import Company, AIModel
from app.services.trend.calculator import EntityCounts, EntityType, compute_trend_scores, TrendResult

logger = structlog.get_logger(__name__)


class TrendAggregator:
    """
    Aggregates article counts and importance scores per entity
    over multiple time windows, then computes trend scores.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def aggregate_all(
        self, target_date: str
    ) -> dict[str, list[TrendResult]]:
        """
        Compute trend results for all entity types.

        Returns:
            {
                "tag":      [TrendResult, ...],
                "company":  [TrendResult, ...],
                "ai_model": [TrendResult, ...],
            }
        """
        d = date.fromisoformat(target_date)

        windows = {
            "1d":      (d - timedelta(days=1),  d),
            "7d":      (d - timedelta(days=7),  d),
            "30d":     (d - timedelta(days=30), d),
            "prev_7d": (d - timedelta(days=14), d - timedelta(days=7)),
        }

        logger.info("trend_aggregation_start", date=target_date)

        tags_ec      = await self._count_tags(windows)
        companies_ec = await self._count_companies(windows)
        models_ec    = await self._count_models(windows)

        max_tag     = max((e.count_7d for e in tags_ec),      default=1)
        max_company = max((e.count_7d for e in companies_ec), default=1)
        max_model   = max((e.count_7d for e in models_ec),    default=1)

        results = {
            EntityType.TAG:      compute_trend_scores(tags_ec,      max_tag),
            EntityType.COMPANY:  compute_trend_scores(companies_ec, max_company),
            EntityType.AI_MODEL: compute_trend_scores(models_ec,    max_model),
        }

        logger.info(
            "trend_aggregation_done",
            tags=len(results[EntityType.TAG]),
            companies=len(results[EntityType.COMPANY]),
            models=len(results[EntityType.AI_MODEL]),
        )
        return results

    # ------------------------------------------------------------------
    # Tag counts
    # ------------------------------------------------------------------

    async def _count_tags(
        self, windows: dict[str, tuple[date, date]]
    ) -> list[EntityCounts]:
        tag_rows = (await self._session.execute(select(Tag))).scalars().all()
        counts: dict[str, EntityCounts] = {
            t.slug: EntityCounts(
                slug=t.slug, name=t.name, entity_type=EntityType.TAG
            )
            for t in tag_rows
        }

        for window_name, (start, end) in windows.items():
            rows = await self._session.execute(
                select(
                    Tag.slug,
                    func.count(NewsArticle.id).label("cnt"),
                    func.avg(NewsArticle.importance_score).label("avg_imp"),
                )
                .join(article_tags, article_tags.c.tag_id == Tag.id)
                .join(NewsArticle, NewsArticle.id == article_tags.c.article_id)
                .where(
                    NewsArticle.is_published.is_(True),
                    NewsArticle.published_at >= _dt(start),
                    NewsArticle.published_at < _dt(end),
                )
                .group_by(Tag.slug)
            )
            for slug, cnt, avg_imp in rows:
                if slug not in counts:
                    continue
                ec = counts[slug]
                _assign_window(ec, window_name, int(cnt), float(avg_imp or 0))

        return list(counts.values())

    # ------------------------------------------------------------------
    # Company counts
    # ------------------------------------------------------------------

    async def _count_companies(
        self, windows: dict[str, tuple[date, date]]
    ) -> list[EntityCounts]:
        co_rows = (await self._session.execute(select(Company))).scalars().all()
        counts: dict[str, EntityCounts] = {
            c.slug: EntityCounts(
                slug=c.slug, name=c.name, entity_type=EntityType.COMPANY
            )
            for c in co_rows
        }

        for window_name, (start, end) in windows.items():
            rows = await self._session.execute(
                select(
                    Company.slug,
                    func.count(NewsArticle.id).label("cnt"),
                    func.avg(NewsArticle.importance_score).label("avg_imp"),
                )
                .join(article_companies, article_companies.c.company_id == Company.id)
                .join(NewsArticle, NewsArticle.id == article_companies.c.article_id)
                .where(
                    NewsArticle.is_published.is_(True),
                    NewsArticle.published_at >= _dt(start),
                    NewsArticle.published_at < _dt(end),
                )
                .group_by(Company.slug)
            )
            for slug, cnt, avg_imp in rows:
                if slug not in counts:
                    continue
                ec = counts[slug]
                _assign_window(ec, window_name, int(cnt), float(avg_imp or 0))

        return list(counts.values())

    # ------------------------------------------------------------------
    # AI Model counts
    # ------------------------------------------------------------------

    async def _count_models(
        self, windows: dict[str, tuple[date, date]]
    ) -> list[EntityCounts]:
        model_rows = (await self._session.execute(select(AIModel))).scalars().all()
        counts: dict[str, EntityCounts] = {
            m.slug: EntityCounts(
                slug=m.slug, name=m.name, entity_type=EntityType.AI_MODEL
            )
            for m in model_rows
        }

        for window_name, (start, end) in windows.items():
            rows = await self._session.execute(
                select(
                    AIModel.slug,
                    func.count(NewsArticle.id).label("cnt"),
                    func.avg(NewsArticle.importance_score).label("avg_imp"),
                )
                .join(article_models, article_models.c.model_id == AIModel.id)
                .join(NewsArticle, NewsArticle.id == article_models.c.article_id)
                .where(
                    NewsArticle.is_published.is_(True),
                    NewsArticle.published_at >= _dt(start),
                    NewsArticle.published_at < _dt(end),
                )
                .group_by(AIModel.slug)
            )
            for slug, cnt, avg_imp in rows:
                if slug not in counts:
                    continue
                ec = counts[slug]
                _assign_window(ec, window_name, int(cnt), float(avg_imp or 0))

        return list(counts.values())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _assign_window(
    ec: EntityCounts, window: str, count: int, avg_importance: float
) -> None:
    if window == "1d":
        ec.count_1d = count
    elif window == "7d":
        ec.count_7d = count
        ec.avg_importance = avg_importance   # use 7d window for importance
    elif window == "30d":
        ec.count_30d = count
    elif window == "prev_7d":
        ec.count_prev_7d = count


def _dt(d: date):
    """Convert date to timezone-aware datetime for SQLAlchemy comparison."""
    from datetime import datetime, timezone
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
