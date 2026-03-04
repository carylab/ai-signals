"""
/api/v1/stats  — platform statistics for dashboard and monitoring
"""
from __future__ import annotations

from datetime import date, timedelta, datetime, timezone

import structlog
from fastapi import APIRouter
from sqlalchemy import desc, func, select

from app.dependencies import DbSession
from app.models.news import NewsArticle
from app.models.source import NewsSource
from app.models.tag import Tag
from app.models.company import Company
from app.models.brief import DailyBrief
from app.models.pipeline_run import PipelineRun
from app.schemas.api import PlatformStats

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.get("", response_model=PlatformStats)
async def platform_stats(db: DbSession) -> PlatformStats:
    """
    Aggregate platform statistics.
    Used by monitoring dashboards and the admin UI.
    """
    # Run all counts concurrently via parallel awaits
    from sqlalchemy import distinct

    total_articles = (
        await db.execute(select(func.count()).select_from(NewsArticle))
    ).scalar_one()

    published_articles = (
        await db.execute(
            select(func.count()).select_from(
                select(NewsArticle).where(NewsArticle.is_published.is_(True)).subquery()
            )
        )
    ).scalar_one()

    total_sources, active_sources = (
        await db.execute(
            select(
                func.count().label("total"),
                func.sum(
                    func.cast(NewsSource.is_active, type_=None)
                ).label("active"),
            )
        )
    ).one()

    total_tags = (
        await db.execute(select(func.count()).select_from(Tag))
    ).scalar_one()

    total_companies = (
        await db.execute(select(func.count()).select_from(Company))
    ).scalar_one()

    total_briefs = (
        await db.execute(
            select(func.count()).select_from(
                select(DailyBrief).where(DailyBrief.is_published.is_(True)).subquery()
            )
        )
    ).scalar_one()

    # Last pipeline run
    last_run = await db.scalar(
        select(PipelineRun).order_by(desc(PipelineRun.started_at)).limit(1)
    )

    # Articles published today (UTC)
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    articles_today = (
        await db.execute(
            select(func.count()).select_from(
                select(NewsArticle)
                .where(
                    NewsArticle.is_published.is_(True),
                    NewsArticle.created_at >= today_start,
                )
                .subquery()
            )
        )
    ).scalar_one()

    # Average daily articles over last 7 days
    week_ago = (date.today() - timedelta(days=7)).isoformat()
    articles_7d = (
        await db.execute(
            select(func.count()).select_from(
                select(NewsArticle)
                .where(
                    NewsArticle.is_published.is_(True),
                    NewsArticle.created_at >= week_ago,
                )
                .subquery()
            )
        )
    ).scalar_one()
    avg_daily_7d = round(articles_7d / 7, 1)

    return PlatformStats(
        total_articles=total_articles,
        published_articles=published_articles,
        total_sources=int(total_sources or 0),
        active_sources=int(active_sources or 0),
        total_tags=total_tags,
        total_companies=total_companies,
        total_briefs=total_briefs,
        last_pipeline_run=(
            last_run.started_at.isoformat() if last_run else None
        ),
        last_pipeline_status=last_run.status if last_run else None,
        articles_today=articles_today,
        avg_daily_articles_7d=avg_daily_7d,
    )


@router.get("/sources")
async def source_stats(db: DbSession) -> list[dict]:
    """Per-source article counts and health status."""
    sources = (
        await db.execute(
            select(NewsSource).order_by(
                NewsSource.priority.asc(),
                NewsSource.total_articles_fetched.desc(),
            )
        )
    ).scalars().all()

    return [
        {
            "slug": s.slug,
            "name": s.name,
            "category": s.category,
            "is_active": s.is_active,
            "priority": s.priority,
            "total_fetched": s.total_articles_fetched,
            "consecutive_errors": s.consecutive_errors,
            "last_fetched_at": s.last_fetched_at,
            "last_error": s.last_error,
        }
        for s in sources
    ]


@router.get("/pipeline/cost")
async def pipeline_cost_summary(
    db: DbSession,
    days: int = 30,
) -> dict:
    """LLM cost summary for the last N days."""
    cutoff = (date.today() - timedelta(days=days)).isoformat()

    rows = (
        await db.execute(
            select(PipelineRun).where(PipelineRun.date >= cutoff)
        )
    ).scalars().all()

    total_cost = sum(r.llm_cost_usd for r in rows)
    total_input = sum(r.llm_input_tokens for r in rows)
    total_output = sum(r.llm_output_tokens for r in rows)
    runs = len(rows)

    return {
        "period_days": days,
        "runs": runs,
        "total_cost_usd": round(total_cost, 4),
        "avg_cost_per_run_usd": round(total_cost / max(runs, 1), 4),
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "daily_breakdown": [
            {
                "date": r.date,
                "cost_usd": r.llm_cost_usd,
                "articles_published": r.articles_published,
            }
            for r in sorted(rows, key=lambda r: r.date)
        ],
    }
