"""
/api/v1/search  — full-text article search

MVP: SQLite FTS via LIKE (works without extension).
V2 upgrade path: swap _search_db() for pgvector semantic search
                 or Meilisearch without changing the route handler.
"""
from __future__ import annotations

import time
from typing import Optional

import structlog
from fastapi import APIRouter, Query
from sqlalchemy import desc, func, or_, select

from app.core.exceptions import ValidationError
from app.dependencies import DbSession, PaginationDep
from app.models.news import NewsArticle
from app.models.tag import Tag
from app.schemas.api import ArticleListItem, PaginatedResponse, SearchResult

router = APIRouter()
logger = structlog.get_logger(__name__)

_MIN_QUERY_LEN = 2
_MAX_QUERY_LEN = 200


@router.get("", response_model=SearchResult)
async def search_articles(
    db: DbSession,
    q: str = Query(..., min_length=_MIN_QUERY_LEN, max_length=_MAX_QUERY_LEN,
                   description="Search query"),
    tag: Optional[str] = Query(default=None, description="Filter by tag slug"),
    company: Optional[str] = Query(default=None, description="Filter by company slug"),
    date_from: Optional[str] = Query(default=None, description="Start date YYYY-MM-DD"),
    date_to: Optional[str] = Query(default=None, description="End date YYYY-MM-DD"),
    min_score: float = Query(default=0.0, ge=0.0, le=1.0),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> SearchResult:
    """
    Search published articles by keyword.

    Searches title and summary fields.
    Results are ranked by final_score (importance × freshness × trend).
    """
    t0 = time.perf_counter()
    q_stripped = q.strip()

    if len(q_stripped) < _MIN_QUERY_LEN:
        raise ValidationError(f"Query too short (min {_MIN_QUERY_LEN} chars)")

    logger.info("search_request", query=q_stripped, tag=tag, company=company)

    stmt = _build_search_query(q_stripped, tag, company, date_from, date_to, min_score)

    # Count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    # Paginate
    offset = (page - 1) * page_size
    articles = (
        await db.execute(stmt.offset(offset).limit(page_size))
    ).scalars().unique().all()

    took_ms = round((time.perf_counter() - t0) * 1000, 1)
    logger.info("search_done", query=q_stripped, total=total, took_ms=took_ms)

    return SearchResult(
        articles=[ArticleListItem.model_validate(a) for a in articles],
        total=total,
        query=q_stripped,
        took_ms=took_ms,
    )


def _build_search_query(
    q: str,
    tag: Optional[str],
    company: Optional[str],
    date_from: Optional[str],
    date_to: Optional[str],
    min_score: float,
):
    pattern = f"%{q}%"

    stmt = (
        select(NewsArticle)
        .where(
            NewsArticle.is_published.is_(True),
            NewsArticle.is_cluster_representative.is_(True),
            NewsArticle.final_score >= min_score,
            or_(
                NewsArticle.title.ilike(pattern),
                NewsArticle.summary.ilike(pattern),
                NewsArticle.clean_content.ilike(pattern),
            ),
        )
        .order_by(desc(NewsArticle.final_score))
    )

    if tag:
        stmt = stmt.join(NewsArticle.tags).where(Tag.slug == tag)

    if company:
        from app.models.company import Company
        stmt = stmt.join(NewsArticle.companies).where(Company.slug == company)

    if date_from:
        from datetime import datetime, timezone
        try:
            dt = datetime.fromisoformat(date_from).replace(tzinfo=timezone.utc)
            stmt = stmt.where(NewsArticle.published_at >= dt)
        except ValueError:
            pass

    if date_to:
        from datetime import datetime, timezone
        try:
            dt = datetime.fromisoformat(date_to).replace(tzinfo=timezone.utc)
            stmt = stmt.where(NewsArticle.published_at <= dt)
        except ValueError:
            pass

    return stmt
