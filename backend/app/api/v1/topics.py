"""
/api/v1/topics  — tag/topic pages
"""
from __future__ import annotations

from fastapi import APIRouter, Query
from sqlalchemy import desc, select

from app.core.exceptions import NotFoundError
from app.dependencies import DbSession, PaginationDep
from app.models.tag import Tag
from app.models.news import NewsArticle
from app.schemas.common import PaginatedResponse
from app.schemas.news import ArticleListItem

router = APIRouter()


@router.get("")
async def list_topics(db: DbSession) -> list[dict]:
    """All tags sorted by trend score."""
    tags = (
        await db.execute(select(Tag).order_by(desc(Tag.trend_score)))
    ).scalars().all()

    return [
        {
            "slug": t.slug,
            "name": t.name,
            "category": t.category,
            "trend_score": t.trend_score,
            "news_count_7d": t.news_count_7d,
            "description": t.description,
        }
        for t in tags
    ]


@router.get("/{slug}")
async def get_topic(slug: str, db: DbSession) -> dict:
    tag = await db.scalar(select(Tag).where(Tag.slug == slug))
    if not tag:
        raise NotFoundError("Topic", slug)

    return {
        "slug": tag.slug,
        "name": tag.name,
        "category": tag.category,
        "description": tag.description,
        "trend_score": tag.trend_score,
        "news_count_7d": tag.news_count_7d,
        "news_count_30d": tag.news_count_30d,
    }


@router.get("/{slug}/news", response_model=PaginatedResponse[ArticleListItem])
async def topic_news(
    slug: str,
    db: DbSession,
    pagination: PaginationDep,
) -> PaginatedResponse[ArticleListItem]:
    tag = await db.scalar(select(Tag).where(Tag.slug == slug))
    if not tag:
        raise NotFoundError("Topic", slug)

    from sqlalchemy import func
    stmt = (
        select(NewsArticle)
        .join(NewsArticle.tags)
        .where(
            Tag.slug == slug,
            NewsArticle.is_published.is_(True),
        )
        .order_by(desc(NewsArticle.final_score))
    )

    total = (
        await db.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()

    articles = (
        await db.execute(stmt.offset(pagination.offset).limit(pagination.limit))
    ).scalars().unique().all()

    return PaginatedResponse.build(
        items=[ArticleListItem.model_validate(a) for a in articles],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )
