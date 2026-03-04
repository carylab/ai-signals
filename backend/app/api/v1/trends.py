"""
/api/v1/trends  — trending tags, companies, and historical snapshots.
Replaces the placeholder written in Step 5.
"""
from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, Query
from sqlalchemy import desc, select

from app.dependencies import DbSession
from app.models.tag import Tag
from app.models.company import Company, AIModel
from app.models.trend_snapshot import TrendSnapshot, EntityType

router = APIRouter()


# ---------------------------------------------------------------------------
# Current trending
# ---------------------------------------------------------------------------

@router.get("/tags")
async def trending_tags(
    db: DbSession,
    limit: int = Query(default=20, ge=1, le=50),
) -> list[dict]:
    """Top tags by current trend_score."""
    tags = (
        await db.execute(
            select(Tag).order_by(desc(Tag.trend_score)).limit(limit)
        )
    ).scalars().all()

    return [
        {
            "slug": t.slug,
            "name": t.name,
            "category": t.category,
            "trend_score": t.trend_score,
            "news_count_7d": t.news_count_7d,
            "news_count_30d": t.news_count_30d,
        }
        for t in tags
    ]


@router.get("/companies")
async def trending_companies(
    db: DbSession,
    limit: int = Query(default=10, ge=1, le=30),
) -> list[dict]:
    """Top companies by current trend_score."""
    companies = (
        await db.execute(
            select(Company).order_by(desc(Company.trend_score)).limit(limit)
        )
    ).scalars().all()

    return [
        {
            "slug": c.slug,
            "name": c.name,
            "trend_score": c.trend_score,
            "news_count_7d": c.news_count_7d,
        }
        for c in companies
    ]


@router.get("/models")
async def trending_models(
    db: DbSession,
    limit: int = Query(default=10, ge=1, le=30),
) -> list[dict]:
    """Top AI models by current trend_score."""
    models = (
        await db.execute(
            select(AIModel).order_by(desc(AIModel.trend_score)).limit(limit)
        )
    ).scalars().all()

    return [
        {
            "slug": m.slug,
            "name": m.name,
            "trend_score": m.trend_score,
            "news_count_7d": m.news_count_7d,
            "is_open_source": m.is_open_source,
        }
        for m in models
    ]


# ---------------------------------------------------------------------------
# Historical snapshots
# ---------------------------------------------------------------------------

@router.get("/history/{entity_type}/{slug}")
async def trend_history(
    entity_type: Literal["tag", "company", "ai_model"],
    slug: str,
    db: DbSession,
    days: int = Query(default=30, ge=7, le=90),
) -> list[dict]:
    """
    Return daily trend_score history for a single entity.
    Useful for sparklines on topic/company pages.
    """
    from datetime import date, timedelta
    cutoff = (date.today() - timedelta(days=days)).isoformat()

    snaps = (
        await db.execute(
            select(TrendSnapshot)
            .where(
                TrendSnapshot.entity_type == entity_type,
                TrendSnapshot.entity_slug == slug,
                TrendSnapshot.date >= cutoff,
            )
            .order_by(TrendSnapshot.date.asc())
        )
    ).scalars().all()

    return [
        {
            "date": s.date,
            "trend_score": s.trend_score,
            "velocity": s.velocity,
            "count_1d": s.count_1d,
            "count_7d": s.count_7d,
        }
        for s in snaps
    ]


@router.get("/snapshot/{date}")
async def daily_snapshot(
    date: str,
    db: DbSession,
    entity_type: Optional[Literal["tag", "company", "ai_model"]] = None,
    limit: int = Query(default=20, ge=1, le=100),
) -> list[dict]:
    """
    Full trend snapshot for a specific date.
    Optional filter by entity_type.
    """
    stmt = (
        select(TrendSnapshot)
        .where(TrendSnapshot.date == date)
        .order_by(desc(TrendSnapshot.trend_score))
        .limit(limit)
    )
    if entity_type:
        stmt = stmt.where(TrendSnapshot.entity_type == entity_type)

    snaps = (await db.execute(stmt)).scalars().all()

    return [
        {
            "entity_type": s.entity_type,
            "slug": s.entity_slug,
            "name": s.entity_name,
            "trend_score": s.trend_score,
            "velocity": s.velocity,
            "count_1d": s.count_1d,
            "count_7d": s.count_7d,
            "count_30d": s.count_30d,
            "avg_importance": s.avg_importance,
        }
        for s in snaps
    ]
