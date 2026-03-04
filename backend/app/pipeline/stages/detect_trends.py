"""
Stage: detect_trends

Runs the TrendDetector after articles are stored.
Updates Tag / Company / AIModel trend scores that feed into:
  - /trending page
  - article scoring (ScoreStage reads these in the next run)
  - Daily Brief trending section

This stage is injected into the pipeline runner between
StoreStage and GeneratePagesStage.
"""
from __future__ import annotations

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.pipeline.base import PipelineContext, PipelineStageBase
from app.services.trend.detector import TrendDetector

logger = structlog.get_logger(__name__)


class DetectTrendsStage(PipelineStageBase):
    name = "detect_trends"

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def process(self, ctx: PipelineContext) -> PipelineContext:
        detector = TrendDetector(self._session)
        summary = await detector.run(target_date=ctx.target_date)

        ctx.set_stage_stat(self.name, "tags_updated", summary["tags_updated"])
        ctx.set_stage_stat(self.name, "companies_updated", summary["companies_updated"])
        ctx.set_stage_stat(self.name, "models_updated", summary["models_updated"])
        ctx.set_stage_stat(self.name, "top_tags", summary["top_tags"])
        ctx.set_stage_stat(self.name, "top_companies", summary["top_companies"])

        return ctx
