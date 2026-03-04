"""
Stage: generate_report

Calls LLM to produce the DailyBrief narrative.
Stores result in daily_briefs table and exports as JSON.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import structlog
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.pipeline.base import PipelineContext, PipelineStageBase
from app.models.brief import DailyBrief
from app.models.news import NewsArticle
from app.models.tag import Tag

logger = structlog.get_logger(__name__)


class GenerateReportStage(PipelineStageBase):
    name = "generate_report"

    def __init__(
        self,
        session: AsyncSession,
        llm_client,
        export_dir: str,
    ) -> None:
        self._session = session
        self._llm = llm_client
        self._export_dir = Path(export_dir)

    async def process(self, ctx: PipelineContext) -> PipelineContext:
        # Fetch top articles for today from DB
        result = await self._session.execute(
            select(NewsArticle)
            .where(
                NewsArticle.is_published.is_(True),
                NewsArticle.is_cluster_representative.is_(True),
            )
            .order_by(desc(NewsArticle.final_score))
            .limit(20)
        )
        top_articles = result.scalars().all()

        if not top_articles:
            ctx.add_error(self.name, "No published articles to generate brief from")
            return ctx

        # Fetch trending tags
        tag_result = await self._session.execute(
            select(Tag).order_by(desc(Tag.trend_score)).limit(10)
        )
        trending_tags = tag_result.scalars().all()

        t0 = time.monotonic()
        brief_data = await self._generate_brief(top_articles, trending_tags, ctx)
        duration = round(time.monotonic() - t0, 2)

        # Upsert DailyBrief
        existing = await self._session.scalar(
            select(DailyBrief).where(DailyBrief.date == ctx.target_date)
        )
        if existing:
            brief = existing
        else:
            brief = DailyBrief(date=ctx.target_date)
            self._session.add(brief)

        brief.headline = brief_data.get("headline", "")
        brief.summary = brief_data.get("summary", "")
        brief.key_themes = json.dumps(brief_data.get("key_themes", []))
        brief.top_story_ids = json.dumps([a.id for a in top_articles[:10]])
        brief.trending_tag_ids = json.dumps([t.id for t in trending_tags[:5]])
        brief.total_articles_processed = ctx.stats.get("collect", {}).get("articles_fetched", 0)
        brief.total_articles_published = ctx.stats.get("store", {}).get("published", 0)
        brief.llm_model_used = self._llm.model
        brief.generation_duration_s = duration
        brief.is_published = True

        await self._session.flush()

        # Export JSON for frontend
        self._export_brief(brief, top_articles, trending_tags)

        ctx.set_stage_stat(self.name, "brief_date", ctx.target_date)
        ctx.set_stage_stat(self.name, "headline", brief.headline[:80])
        return ctx

    async def _generate_brief(
        self,
        articles: list[NewsArticle],
        tags: list[Tag],
        ctx: PipelineContext,
    ) -> dict:
        from app.services.llm.prompts.brief import BRIEF_SYSTEM, build_brief_prompt

        # Build compact article summaries for the prompt
        article_inputs = [
            {
                "title": a.title,
                "summary": a.summary or "",
                "source": a.source_id,
                "score": a.final_score,
            }
            for a in articles[:15]
        ]
        trending_input = [t.name for t in tags]

        try:
            response = await self._llm.complete_json(
                system=BRIEF_SYSTEM,
                user=build_brief_prompt(
                    date=ctx.target_date,
                    articles=article_inputs,
                    trending_tags=trending_input,
                ),
            )
            return response
        except Exception as exc:
            ctx.add_error(self.name, f"LLM brief generation failed: {exc}")
            # Fallback: use top article title as headline
            return {
                "headline": articles[0].title if articles else "AI News Update",
                "summary": "\n\n".join(
                    a.summary for a in articles[:5] if a.summary
                ),
                "key_themes": [t.name for t in tags[:5]],
            }

    def _export_brief(
        self,
        brief: DailyBrief,
        articles: list[NewsArticle],
        tags: list[Tag],
    ) -> None:
        payload = {
            "date": brief.date,
            "headline": brief.headline,
            "summary": brief.summary,
            "key_themes": json.loads(brief.key_themes or "[]"),
            "top_stories": [
                {
                    "id": a.id,
                    "slug": a.slug,
                    "title": a.title,
                    "summary": a.summary or "",
                    "final_score": a.final_score,
                    "published_at": a.published_at.isoformat() if a.published_at else None,
                }
                for a in articles[:10]
            ],
            "trending_tags": [
                {"slug": t.slug, "name": t.name, "trend_score": t.trend_score}
                for t in tags[:8]
            ],
            "stats": {
                "articles_processed": brief.total_articles_processed,
                "articles_published": brief.total_articles_published,
            },
        }
        out_path = self._export_dir / "daily" / f"{brief.date}.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        logger.info("brief_exported", path=str(out_path))
