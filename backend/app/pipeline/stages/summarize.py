"""
Stage: summarize

Calls LLM to generate:
  - 2-3 sentence summary
  - 3 bullet points
  - meta_description (≤160 chars, SEO-ready)

Only processes cluster representatives to minimise LLM cost.
Non-representatives inherit their cluster rep's summary.

Uses asyncio.gather with concurrency semaphore to parallelise calls.
"""
from __future__ import annotations

import asyncio
import json
from typing import Optional

import structlog

from app.pipeline.base import PipelineContext, PipelineStageBase

logger = structlog.get_logger(__name__)

_CONCURRENCY = 5   # parallel LLM calls; adjust based on rate limits


class SummarizeStage(PipelineStageBase):
    name = "summarize"

    def __init__(self, llm_client) -> None:
        # llm_client: BaseLLMClient (injected by runner)
        self._llm = llm_client

    async def process(self, ctx: PipelineContext) -> PipelineContext:
        # Separate reps from non-reps
        reps = [a for a in ctx.articles if a.get("is_cluster_representative", True)]
        non_reps = [a for a in ctx.articles if not a.get("is_cluster_representative", True)]

        sem = asyncio.Semaphore(_CONCURRENCY)
        tasks = [self._summarize_one(a, sem, ctx) for a in reps]
        summarized_reps = list(await asyncio.gather(*tasks))

        # Build lookup by cluster_id so non-reps can inherit
        rep_by_cluster: dict[int, dict] = {}
        for a in summarized_reps:
            cid = a.get("cluster_id")
            if cid is not None:
                rep_by_cluster[cid] = a

        # Non-reps inherit summary from their cluster representative
        for a in non_reps:
            cid = a.get("cluster_id")
            rep = rep_by_cluster.get(cid) if cid is not None else None
            if rep:
                a["summary"] = rep.get("summary", "")
                a["summary_bullets"] = rep.get("summary_bullets", "[]")
                a["meta_description"] = rep.get("meta_description", "")
                a["llm_model_used"] = rep.get("llm_model_used", "")

        ctx.articles = summarized_reps + non_reps

        ok = sum(1 for a in ctx.articles if a.get("summary"))
        ctx.set_stage_stat(self.name, "summarized", ok)
        ctx.set_stage_stat(self.name, "skipped_non_rep", len(non_reps))
        ctx.set_stage_stat(self.name, "llm_calls", len(reps))
        return ctx

    async def _summarize_one(
        self,
        article: dict,
        sem: asyncio.Semaphore,
        ctx: PipelineContext,
    ) -> dict:
        async with sem:
            content = article.get("clean_content") or article.get("title", "")
            content_snippet = content[:3000]  # keep tokens manageable

            try:
                from app.services.llm.prompts.summarize import (
                    SUMMARIZE_SYSTEM,
                    build_summarize_prompt,
                )
                response = await self._llm.complete_json(
                    system=SUMMARIZE_SYSTEM,
                    user=build_summarize_prompt(
                        title=article["title"],
                        content=content_snippet,
                        source=article.get("source_slug", ""),
                    ),
                )

                article["summary"] = response.get("summary", "")
                article["summary_bullets"] = json.dumps(
                    response.get("bullets", [])
                )
                article["meta_description"] = response.get(
                    "meta_description", ""
                )[:160]
                article["llm_model_used"] = self._llm.model

                # Accumulate token costs in context
                ctx.llm_input_tokens += getattr(response, "_input_tokens", 0)
                ctx.llm_output_tokens += getattr(response, "_output_tokens", 0)

            except Exception as exc:
                ctx.add_error(self.name, f"url={article.get('url', '?')}: {exc}")
                # Fallback: use first 160 chars of content as summary
                article["summary"] = content[:200]
                article["summary_bullets"] = "[]"
                article["meta_description"] = content[:160]

            return article
