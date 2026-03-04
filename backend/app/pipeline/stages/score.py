"""
Stage: score

Computes all four scoring dimensions for every article and
writes final_score using the ranker's weighted combination.

Uses the dedicated scoring service modules:
  services/scoring/importance.py
  services/scoring/freshness.py
  services/scoring/trend_score.py
  services/scoring/discussion.py
  services/scoring/ranker.py

Trend scores for tags/companies/models are pre-loaded once
per run by the PipelineRunner and passed in at construction time.
"""
from __future__ import annotations

from datetime import datetime, timezone

import structlog

from app.pipeline.base import PipelineContext, PipelineStageBase
from app.services.scoring.importance import compute_importance
from app.services.scoring.freshness import compute_freshness
from app.services.scoring.trend_score import compute_trend
from app.services.scoring.discussion import compute_discussion
from app.services.scoring.ranker import compute_final_score

logger = structlog.get_logger(__name__)


class ScoreStage(PipelineStageBase):
    name = "score"

    def __init__(
        self,
        tag_trend_scores: dict[str, float] | None = None,
        company_trend_scores: dict[str, float] | None = None,
        model_trend_scores: dict[str, float] | None = None,
    ) -> None:
        self._tag_trends     = tag_trend_scores     or {}
        self._company_trends = company_trend_scores or {}
        self._model_trends   = model_trend_scores   or {}

    async def process(self, ctx: PipelineContext) -> PipelineContext:
        now = datetime.now(timezone.utc)

        for article in ctx.articles:
            scores = self._score_article(article, now)
            article.update(scores)

        # Pipeline stats
        final_scores = [a["final_score"] for a in ctx.articles]
        if final_scores:
            ctx.set_stage_stat(self.name, "count",     len(final_scores))
            ctx.set_stage_stat(self.name, "avg_score", round(sum(final_scores) / len(final_scores), 3))
            ctx.set_stage_stat(self.name, "max_score", round(max(final_scores), 3))
            ctx.set_stage_stat(self.name, "min_score", round(min(final_scores), 3))
            above_threshold = sum(1 for s in final_scores if s >= 0.25)
            ctx.set_stage_stat(self.name, "above_publish_threshold", above_threshold)

        return ctx

    def _score_article(self, article: dict, now: datetime) -> dict:
        importance = compute_importance(
            source_priority=article.get("source_priority", 5),
            title=article.get("title", ""),
            tags=article.get("tags", []),
            companies=article.get("companies", []),
            word_count=article.get("word_count", 0),
        )

        freshness = compute_freshness(
            published_at=article.get("published_at"),
            now=now,
        )

        trend = compute_trend(
            tags=article.get("tags", []),
            companies=article.get("companies", []),
            ai_models=article.get("ai_models", []),
            tag_trend_scores=self._tag_trends,
            company_trend_scores=self._company_trends,
            model_trend_scores=self._model_trends,
        )

        discussion = compute_discussion(
            cluster_size=article.get("cluster_size", 1),
            source_category=article.get("source_category", ""),
        )

        final = compute_final_score(importance, freshness, trend, discussion)

        return {
            "importance_score":  round(importance, 4),
            "freshness_score":   round(freshness,  4),
            "trend_score":       round(trend,       4),
            "discussion_score":  round(discussion,  4),
            "final_score":       round(final,       4),
        }
