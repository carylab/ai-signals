"""
/api/v1/news  — article listing, detail, search
"""
from __future__ import annotations

from typing import Optional

import structlog
from fastapi import APIRouter, Query
from sqlalchemy import desc, func, or_, select

from app.core.exceptions import NotFoundError
from app.dependencies import DbSession, PaginationDep
from app.models.news import NewsArticle
from app.models.tag import Tag
from app.schemas.common import PaginatedResponse
from app.schemas.news import ArticleDetail, ArticleListItem

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.get("", response_model=PaginatedResponse[ArticleListItem])
async def list_articles(
    db: DbSession,
    pagination: PaginationDep,
    q: Optional[str] = Query(default=None, description="Full-text search"),
    tag: Optional[str] = Query(default=None, description="Filter by tag slug"),
    company: Optional[str] = Query(default=None, description="Filter by company slug"),
    date: Optional[str] = Query(default=None, description="Filter by date YYYY-MM-DD"),
    min_score: float = Query(default=0.0, ge=0.0, le=1.0),
    reps_only: bool = Query(default=True, description="Only cluster representatives"),
) -> PaginatedResponse[ArticleListItem]:
    """
    List published articles.  Supports filtering and pagination.
    """
    stmt = (
        select(NewsArticle)
        .where(
            NewsArticle.is_published.is_(True),
            NewsArticle.final_score >= min_score,
        )
        .order_by(desc(NewsArticle.final_score))
    )

    if reps_only:
        stmt = stmt.where(NewsArticle.is_cluster_representative.is_(True))

    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(
            or_(
                NewsArticle.title.ilike(pattern),
                NewsArticle.summary.ilike(pattern),
            )
        )

    if tag:
        stmt = stmt.join(NewsArticle.tags).where(Tag.slug == tag)

    if date:
        stmt = stmt.where(
            func.substr(func.cast(NewsArticle.published_at, type_=None), 1, 10) == date
        )

    # Count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    # Paginate
    stmt = stmt.offset(pagination.offset).limit(pagination.limit)
    articles = (await db.execute(stmt)).scalars().unique().all()

    return PaginatedResponse.build(
        items=[ArticleListItem.model_validate(a) for a in articles],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get("/top", response_model=list[ArticleListItem])
async def top_articles(
    db: DbSession,
    limit: int = Query(default=10, ge=1, le=50),
) -> list[ArticleListItem]:
    """Top articles by final_score. Used for homepage."""
    stmt = (
        select(NewsArticle)
        .where(
            NewsArticle.is_published.is_(True),
            NewsArticle.is_cluster_representative.is_(True),
        )
        .order_by(desc(NewsArticle.final_score))
        .limit(limit)
    )
    articles = (await db.execute(stmt)).scalars().all()
    return [ArticleListItem.model_validate(a) for a in articles]


@router.get("/{slug}", response_model=ArticleDetail)
async def get_article(slug: str, db: DbSession) -> ArticleDetail:
    """Get a single article by slug."""
    article = await db.scalar(
        select(NewsArticle).where(
            NewsArticle.slug == slug,
            NewsArticle.is_published.is_(True),
        )
    )
    if not article:
        raise NotFoundError("Article", slug)

    logger.info("article_viewed", slug=slug, score=article.final_score)
    return ArticleDetail.model_validate(article)
