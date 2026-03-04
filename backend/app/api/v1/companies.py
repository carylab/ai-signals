"""
/api/v1/companies  — company profile pages
"""
from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import desc, select

from app.core.exceptions import NotFoundError
from app.dependencies import DbSession, PaginationDep
from app.models.company import Company
from app.models.news import NewsArticle
from app.schemas.common import PaginatedResponse
from app.schemas.news import ArticleListItem

router = APIRouter()


@router.get("")
async def list_companies(db: DbSession) -> list[dict]:
    companies = (
        await db.execute(
            select(Company).order_by(desc(Company.trend_score))
        )
    ).scalars().all()
    return [
        {
            "slug": c.slug,
            "name": c.name,
            "description": c.description,
            "trend_score": c.trend_score,
            "news_count_7d": c.news_count_7d,
        }
        for c in companies
    ]


@router.get("/{slug}")
async def get_company(slug: str, db: DbSession) -> dict:
    company = await db.scalar(select(Company).where(Company.slug == slug))
    if not company:
        raise NotFoundError("Company", slug)

    return {
        "slug": company.slug,
        "name": company.name,
        "description": company.description,
        "website": company.website,
        "country": company.country,
        "founded_year": company.founded_year,
        "trend_score": company.trend_score,
        "news_count_7d": company.news_count_7d,
        "news_count_30d": company.news_count_30d,
    }


@router.get("/{slug}/news", response_model=PaginatedResponse[ArticleListItem])
async def company_news(
    slug: str,
    db: DbSession,
    pagination: PaginationDep,
) -> PaginatedResponse[ArticleListItem]:
    company = await db.scalar(select(Company).where(Company.slug == slug))
    if not company:
        raise NotFoundError("Company", slug)

    from sqlalchemy import func
    stmt = (
        select(NewsArticle)
        .join(NewsArticle.companies)
        .where(
            Company.slug == slug,
            NewsArticle.is_published.is_(True),
        )
        .order_by(desc(NewsArticle.published_at))
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
