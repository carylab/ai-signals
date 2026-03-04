"""
Pipeline runner — orchestrates all stages in order.

Usage:
    runner = PipelineRunner(session, llm_client, settings)
    await runner.run(target_date="2026-03-04")
"""
from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone
from typing import Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.pipeline.base import PipelineContext
from app.pipeline.stages.collect import CollectStage
from app.pipeline.stages.extract import ExtractStage
from app.pipeline.stages.clean import CleanStage
from app.pipeline.stages.deduplicate import DeduplicateStage
from app.pipeline.stages.cluster import ClusterStage
from app.pipeline.stages.summarize import SummarizeStage
from app.pipeline.stages.tag import TagStage
from app.pipeline.stages.score import ScoreStage
from app.pipeline.stages.store import StoreStage
from app.pipeline.stages.detect_trends import DetectTrendsStage
from app.pipeline.stages.generate_pages import GeneratePagesStage
from app.pipeline.stages.generate_report import GenerateReportStage
from app.models.pipeline_run import PipelineRun, RunStatus
from app.models.tag import Tag

logger = structlog.get_logger(__name__)


class PipelineRunner:
    def __init__(
        self,
        session: AsyncSession,
        llm_client,
        export_dir: str,
    ) -> None:
        self._session = session
        self._llm = llm_client
        self._export_dir = export_dir

    async def run(
        self, target_date: Optional[str] = None
    ) -> PipelineContext:
        target_date = target_date or date.today().isoformat()
        run_id = str(uuid.uuid4())

        log = logger.bind(run_id=run_id, date=target_date)
        log.info("pipeline_start")

        # Create audit record
        run_record = PipelineRun(
            run_id=run_id,
            date=target_date,
            status=RunStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
        )
        self._session.add(run_record)
        await self._session.flush()

        ctx = PipelineContext(run_id=run_id, target_date=target_date)

        # Pre-load trend scores for scoring stage
        tag_trends, company_trends, model_trends = await self._load_trend_scores()

        # Build stage list
        stages = [
            CollectStage(self._session),
            ExtractStage(),
            CleanStage(),
            DeduplicateStage(self._session),
            ClusterStage(),
            SummarizeStage(self._llm),
            TagStage(self._llm),
            ScoreStage(
                tag_trend_scores=tag_trends,
                company_trend_scores=company_trends,
                model_trend_scores=model_trends,
            ),
            StoreStage(self._session),
            DetectTrendsStage(self._session),
            GeneratePagesStage(self._session, self._export_dir),
            GenerateReportStage(self._session, self._llm, self._export_dir),
        ]

        # Pre-processing: enrich articles with cluster_size after ClusterStage
        # This is handled inline in the runner loop below.

        for i, stage in enumerate(stages):
            ctx = await stage.safe_run(ctx)

            # Post-cluster hook: annotate cluster_size for scoring
            if stage.name == "cluster":
                _annotate_cluster_sizes(ctx)

            # Commit after each stage so partial progress is durable
            await self._session.commit()

            # Abort if fatal (no articles remain after dedup)
            if stage.name == "deduplicate" and not ctx.articles:
                log.warning("pipeline_no_articles_after_dedup")
                break

        # Finalise audit record
        finished = datetime.now(timezone.utc)
        run_record.finished_at = finished
        run_record.duration_s = (finished - run_record.started_at).total_seconds()
        run_record.status = (
            RunStatus.PARTIAL if ctx.errors else RunStatus.SUCCESS
        )
        run_record.articles_collected = ctx.stats.get("collect", {}).get("articles_fetched", 0)
        run_record.articles_after_dedup = ctx.stats.get("deduplicate", {}).get("after", 0)
        run_record.articles_analyzed = ctx.stats.get("summarize", {}).get("summarized", 0)
        run_record.articles_published = ctx.stats.get("store", {}).get("published", 0)
        run_record.llm_input_tokens = ctx.llm_input_tokens
        run_record.llm_output_tokens = ctx.llm_output_tokens
        run_record.llm_cost_usd = ctx.llm_cost_usd
        run_record.stage_stats = json.dumps(ctx.stats)
        run_record.error_log = json.dumps(ctx.errors)

        await self._session.commit()

        log.info(
            "pipeline_complete",
            status=run_record.status,
            duration_s=run_record.duration_s,
            collected=run_record.articles_collected,
            published=run_record.articles_published,
            errors=len(ctx.errors),
        )

        return ctx

    async def _load_trend_scores(
        self,
    ) -> tuple[dict[str, float], dict[str, float], dict[str, float]]:
        """Load current trend scores for tags, companies, and AI models."""
        from sqlalchemy import select
        from app.models.company import Company, AIModel

        tags = (await self._session.execute(select(Tag))).scalars().all()
        companies = (await self._session.execute(select(Company))).scalars().all()
        models = (await self._session.execute(select(AIModel))).scalars().all()

        return (
            {t.slug: t.trend_score for t in tags},
            {c.slug: c.trend_score for c in companies},
            {m.slug: m.trend_score for m in models},
        )


def _annotate_cluster_sizes(ctx: PipelineContext) -> None:
    """Count cluster members and annotate each article with cluster_size."""
    from collections import Counter
    counts: Counter = Counter(
        a.get("cluster_id") for a in ctx.articles if a.get("cluster_id") is not None
    )
    for article in ctx.articles:
        cid = article.get("cluster_id")
        article["cluster_size"] = counts.get(cid, 1) if cid is not None else 1
