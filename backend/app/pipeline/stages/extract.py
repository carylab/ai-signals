"""
Stage: extract

For each collected article, fetches full page content if only a
summary/snippet was available from the RSS feed.
Uses readability-lxml to extract clean article body.
"""
from __future__ import annotations

import asyncio
from typing import cast

import structlog

from app.pipeline.base import PipelineContext, PipelineStageBase

logger = structlog.get_logger(__name__)

_CONCURRENCY = 10
_MIN_CONTENT_LENGTH = 200  # chars; below this we attempt full-page fetch


class ExtractStage(PipelineStageBase):
    name = "extract"

    async def process(self, ctx: PipelineContext) -> PipelineContext:
        from app.services.crawler.content_extractor import ContentExtractor

        extractor = ContentExtractor()
        sem = asyncio.Semaphore(_CONCURRENCY)

        tasks = [
            self._extract_one(article, extractor, sem, ctx)
            for article in ctx.articles
        ]
        ctx.articles = list(await asyncio.gather(*tasks))

        ok = sum(1 for a in ctx.articles if a.get("clean_content"))
        ctx.set_stage_stat(self.name, "extracted_ok", ok)
        ctx.set_stage_stat(self.name, "extracted_fail", len(ctx.articles) - ok)
        return ctx

    async def _extract_one(
        self,
        article: dict,
        extractor: "ContentExtractor",
        sem: asyncio.Semaphore,
        ctx: PipelineContext,
    ) -> dict:
        async with sem:
            raw = article.get("raw_content", "")
            needs_fetch = len(raw) < _MIN_CONTENT_LENGTH

            try:
                if needs_fetch:
                    full_html = await extractor.fetch_html(article["url"])
                    article["raw_content"] = full_html

                result = extractor.extract(
                    article.get("raw_content", ""),
                    article["url"],
                )
                article.update(result)

            except Exception as exc:
                ctx.add_error(self.name, f"url={article['url']}: {exc}")
                # Keep what we have; don't drop the article
                if not article.get("clean_content"):
                    article["clean_content"] = article.get("title", "")

            return article
