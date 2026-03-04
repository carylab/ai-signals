"""
/api/v1/briefs — daily brief listing and detail
"""
from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, Query
from sqlalchemy import desc, select

from app.core.exceptions import NotFoundError
from app.dependencies import DbSession, PaginationDep
from app.models.brief import DailyBrief
from app.models.news import NewsArticle
from app.models.tag import Tag
from app.schemas.brief import DailyBriefDetail, DailyBriefSchema
from app.schemas.common import PaginatedResponse

router = APIRouter()


@router.get("", response_model=PaginatedResponse[DailyBriefSchema])
async def list_briefs(
    db: DbSession,
    pagination: PaginationDep,
) -> PaginatedResponse[DailyBriefSchema]:
    """List all published daily briefs, newest first."""
    from sqlalchemy import func
    total = (
        await db.execute(
            select(func.count()).select_from(
                select(DailyBrief).where(DailyBrief.is_published.is_(True)).subquery()
            )
        )
    ).scalar_one()

    briefs = (
        await db.execute(
            select(DailyBrief)
            .where(DailyBrief.is_published.is_(True))
            .order_by(desc(DailyBrief.date))
            .offset(pagination.offset)
            .limit(pagination.limit)
        )
    ).scalars().all()

    return PaginatedResponse.build(
        items=[DailyBriefSchema.model_validate(b) for b in briefs],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get("/latest", response_model=DailyBriefDetail)
async def latest_brief(db: DbSession) -> DailyBriefDetail:
    """Get the most recent published daily brief with top stories."""
    brief = await db.scalar(
        select(DailyBrief)
        .where(DailyBrief.is_published.is_(True))
        .order_by(desc(DailyBrief.date))
        .limit(1)
    )
    if not brief:
        raise NotFoundError("DailyBrief", "latest")

    return await _build_brief_detail(brief, db)


@router.get("/{date}", response_model=DailyBriefDetail)
async def get_brief(date: str, db: DbSession) -> DailyBriefDetail:
    """Get brief for a specific date (YYYY-MM-DD)."""
    brief = await db.scalar(
        select(DailyBrief).where(DailyBrief.date == date)
    )
    if not brief:
        raise NotFoundError("DailyBrief", date)

    return await _build_brief_detail(brief, db)


async def _build_brief_detail(brief: DailyBrief, db) -> DailyBriefDetail:
    """Hydrate top_stories from stored IDs."""
    story_ids: list[int] = json.loads(brief.top_story_ids or "[]")
    tag_ids: list[int] = json.loads(brief.trending_tag_ids or "[]")

    stories: list[NewsArticle] = []
    if story_ids:
        result = await db.execute(
            select(NewsArticle).where(NewsArticle.id.in_(story_ids))
        )
        id_to_article = {a.id: a for a in result.scalars().all()}
        # Preserve order
        stories = [id_to_article[i] for i in story_ids if i in id_to_article]

    tags: list[Tag] = []
    if tag_ids:
        result = await db.execute(select(Tag).where(Tag.id.in_(tag_ids)))
        tags = list(result.scalars().all())

    from app.schemas.brief import BriefTopStory, DailyBriefDetail
    import json as _json

    return DailyBriefDetail(
        **DailyBriefSchema.model_validate(brief).model_dump(),
        top_stories=[
            BriefTopStory(
                id=a.id,
                slug=a.slug,
                title=a.title,
                summary=a.summary,
                final_score=a.final_score,
                published_at=a.published_at.isoformat() if a.published_at else None,
            )
            for a in stories
        ],
        trending_tag_slugs=[t.slug for t in tags],
    )
