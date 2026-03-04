"""
Stage: generate_pages

Exports processed articles and metadata as JSON files consumed by
the Next.js frontend during static generation (SSG).

Output layout (under settings.export_dir):
  news/
    {slug}.json         — individual article page
  daily/
    {date}.json         — daily brief data
  indexes/
    latest.json         — top 50 articles for homepage
    trending.json       — top topics by trend_score
    companies.json      — all company pages index
"""
from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path

import structlog
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.pipeline.base import PipelineContext, PipelineStageBase
from app.models.news import NewsArticle
from app.models.tag import Tag
from app.models.company import Company

logger = structlog.get_logger(__name__)


class GeneratePagesStage(PipelineStageBase):
    name = "generate_pages"

    def __init__(self, session: AsyncSession, export_dir: str) -> None:
        self._session = session
        self._export_dir = Path(export_dir)

    async def process(self, ctx: PipelineContext) -> PipelineContext:
        self._export_dir.mkdir(parents=True, exist_ok=True)
        (self._export_dir / "news").mkdir(exist_ok=True)
        (self._export_dir / "daily").mkdir(exist_ok=True)
        (self._export_dir / "indexes").mkdir(exist_ok=True)

        # Export individual article pages
        article_count = await self._export_articles(ctx)

        # Export index files
        await self._export_latest_index()
        await self._export_trending_index()

        ctx.set_stage_stat(self.name, "pages_generated", article_count)
        logger.info("pages_generated", count=article_count, dir=str(self._export_dir))
        return ctx

    async def _export_articles(self, ctx: PipelineContext) -> int:
        count = 0
        for article in ctx.articles:
            db_id = article.get("db_id")
            if not db_id:
                continue
            slug = article.get("slug", "")
            if not slug:
                continue

            payload = {
                "id": db_id,
                "slug": slug,
                "title": article.get("title", ""),
                "url": article.get("url", ""),
                "source": article.get("source_slug", ""),
                "published_at": article.get("published_at", ""),
                "summary": article.get("summary", ""),
                "summary_bullets": _parse_json_field(
                    article.get("summary_bullets", "[]"), []
                ),
                "tags": article.get("tags", []),
                "companies": article.get("companies", []),
                "ai_models": article.get("ai_models", []),
                "importance_score": article.get("importance_score", 0),
                "final_score": article.get("final_score", 0),
                "meta_description": article.get("meta_description", ""),
                "image_url": article.get("image_url"),
                "is_cluster_representative": article.get(
                    "is_cluster_representative", True
                ),
            }
            out_path = self._export_dir / "news" / f"{slug}.json"
            _write_json(out_path, payload)
            count += 1
        return count

    async def _export_latest_index(self) -> None:
        result = await self._session.execute(
            select(NewsArticle)
            .where(NewsArticle.is_published.is_(True))
            .order_by(desc(NewsArticle.final_score))
            .limit(100)
        )
        articles = result.scalars().all()
        payload = [_article_summary(a) for a in articles]
        _write_json(self._export_dir / "indexes" / "latest.json", payload)

    async def _export_trending_index(self) -> None:
        result = await self._session.execute(
            select(Tag).order_by(desc(Tag.trend_score)).limit(20)
        )
        tags = result.scalars().all()
        payload = [
            {
                "slug": t.slug,
                "name": t.name,
                "trend_score": t.trend_score,
                "news_count_7d": t.news_count_7d,
            }
            for t in tags
        ]
        _write_json(self._export_dir / "indexes" / "trending.json", payload)


def _article_summary(a: NewsArticle) -> dict:
    return {
        "id": a.id,
        "slug": a.slug,
        "title": a.title,
        "published_at": a.published_at.isoformat() if a.published_at else None,
        "summary": a.summary or "",
        "final_score": a.final_score,
        "meta_description": a.meta_description or "",
    }


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _parse_json_field(value: str, default):
    try:
        return json.loads(value)
    except Exception:
        return default
