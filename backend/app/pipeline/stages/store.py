"""
Stage: store

Persists all processed articles to the database.
Also upserts Tag, Company, and AIModel records discovered in this run.
Uses bulk insert with conflict handling for efficiency.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.pipeline.base import PipelineContext, PipelineStageBase
from app.models.news import NewsArticle, PipelineStage, article_tags, article_companies, article_models
from app.models.tag import Tag
from app.models.company import Company, AIModel
from app.models.source import NewsSource

logger = structlog.get_logger(__name__)

_MIN_SCORE_TO_PUBLISH = 0.25


class StoreStage(PipelineStageBase):
    name = "store"

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def process(self, ctx: PipelineContext) -> PipelineContext:
        tag_cache: dict[str, Tag] = {}
        company_cache: dict[str, Company] = {}
        model_cache: dict[str, AIModel] = {}

        stored = 0
        published = 0
        errors = 0

        for article in ctx.articles:
            try:
                db_article = await self._store_article(
                    article, tag_cache, company_cache, model_cache
                )
                article["db_id"] = db_article.id
                stored += 1
                if db_article.is_published:
                    published += 1
            except Exception as exc:
                ctx.add_error(self.name, f"url={article.get('url', '?')}: {exc}")
                errors += 1

        await self._session.flush()

        ctx.set_stage_stat(self.name, "stored", stored)
        ctx.set_stage_stat(self.name, "published", published)
        ctx.set_stage_stat(self.name, "errors", errors)
        return ctx

    async def _store_article(
        self,
        data: dict,
        tag_cache: dict[str, Tag],
        company_cache: dict[str, Company],
        model_cache: dict[str, AIModel],
    ) -> NewsArticle:
        # Check for existing record (race condition guard)
        existing = await self._session.scalar(
            select(NewsArticle).where(NewsArticle.url_hash == data["url_hash"])
        )
        if existing:
            return existing

        is_published = (
            data.get("final_score", 0) >= _MIN_SCORE_TO_PUBLISH
            and bool(data.get("summary"))
        )

        pub_at: Optional[datetime] = None
        pub_str = data.get("published_at")
        if pub_str:
            try:
                pub_at = datetime.fromisoformat(pub_str)
            except ValueError:
                pub_at = None

        article = NewsArticle(
            url=data["url"],
            url_hash=data["url_hash"],
            slug=data.get("slug", data["url_hash"][:50]),
            title=data["title"],
            raw_content=data.get("raw_content", "")[:10_000],
            clean_content=data.get("clean_content", ""),
            author=data.get("author"),
            image_url=data.get("image_url"),
            word_count=data.get("word_count", 0),
            source_id=data["source_id"],
            published_at=pub_at,
            fetched_at=datetime.now(timezone.utc),
            summary=data.get("summary"),
            summary_bullets=data.get("summary_bullets", "[]"),
            llm_model_used=data.get("llm_model_used"),
            sim_hash=data.get("sim_hash"),
            cluster_id=data.get("cluster_id"),
            is_cluster_representative=data.get("is_cluster_representative", True),
            importance_score=data.get("importance_score", 0.0),
            freshness_score=data.get("freshness_score", 0.0),
            trend_score=data.get("trend_score", 0.0),
            discussion_score=data.get("discussion_score", 0.0),
            final_score=data.get("final_score", 0.0),
            meta_description=data.get("meta_description"),
            pipeline_stage=PipelineStage.PUBLISHED if is_published else PipelineStage.SCORED,
            is_published=is_published,
        )
        self._session.add(article)
        await self._session.flush()  # get article.id

        # Attach tags
        for tag_name in (data.get("tags") or []):
            tag = await self._get_or_create_tag(tag_name, tag_cache)
            if tag and tag not in article.tags:
                article.tags.append(tag)

        # Attach companies
        for co_name in (data.get("companies") or []):
            company = await self._get_or_create_company(co_name, company_cache)
            if company and company not in article.companies:
                article.companies.append(company)

        # Attach AI models
        for model_name in (data.get("ai_models") or []):
            model = await self._get_or_create_model(model_name, model_cache)
            if model and model not in article.ai_models:
                article.ai_models.append(model)

        return article

    async def _get_or_create_tag(self, name: str, cache: dict) -> Optional[Tag]:
        slug = _to_slug(name)
        if slug in cache:
            return cache[slug]
        tag = await self._session.scalar(select(Tag).where(Tag.slug == slug))
        if not tag:
            tag = Tag(name=name, slug=slug)
            self._session.add(tag)
            await self._session.flush()
        cache[slug] = tag
        return tag

    async def _get_or_create_company(self, name: str, cache: dict) -> Optional[Company]:
        slug = _to_slug(name)
        if slug in cache:
            return cache[slug]
        company = await self._session.scalar(
            select(Company).where(Company.slug == slug)
        )
        if not company:
            company = Company(name=name, slug=slug)
            self._session.add(company)
            await self._session.flush()
        cache[slug] = company
        return company

    async def _get_or_create_model(self, name: str, cache: dict) -> Optional[AIModel]:
        slug = _to_slug(name)
        if slug in cache:
            return cache[slug]
        model = await self._session.scalar(
            select(AIModel).where(AIModel.slug == slug)
        )
        if not model:
            model = AIModel(name=name, slug=slug)
            self._session.add(model)
            await self._session.flush()
        cache[slug] = model
        return model


def _to_slug(name: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
