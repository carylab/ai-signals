"""
Pipeline base classes.

PipelineContext  — shared state passed between all stages
PipelineStageBase — abstract base every stage must implement
"""
from __future__ import annotations

import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ArticleDict(dict):
    """
    Typed alias for raw article dicts flowing through the pipeline.
    Using a plain dict (not a dataclass) keeps stages loosely coupled —
    each stage adds keys without breaking earlier stages.

    Guaranteed keys after each stage:
      collect:     url, url_hash, title, source_id, source_slug,
                   published_at, raw_content, fetched_at
      extract:     clean_content, author, image_url, word_count
      clean:       title (cleaned), clean_content (cleaned)
      deduplicate: sim_hash, _skip (True if duplicate)
      cluster:     cluster_id, is_cluster_representative
      summarize:   summary, summary_bullets, llm_model_used
      tag:         tags (list[str]), companies (list[str]),
                   ai_models (list[str]), entities (dict)
      score:       importance_score, freshness_score, trend_score,
                   discussion_score, final_score
      store:       db_id (int)
    """


@dataclass
class PipelineContext:
    """Shared state container passed through every pipeline stage."""

    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    target_date: str = field(
        default_factory=lambda: date.today().isoformat()
    )

    # Article buckets
    raw_articles: list[dict] = field(default_factory=list)
    articles: list[dict] = field(default_factory=list)
    # articles is the working list; stages mutate it in-place

    # Per-stage statistics
    stats: dict[str, Any] = field(default_factory=dict)

    # Accumulated errors (non-fatal); fatal errors raise exceptions
    errors: list[str] = field(default_factory=list)

    # LLM cost accumulator
    llm_input_tokens: int = 0
    llm_output_tokens: int = 0
    llm_cost_usd: float = 0.0

    # Timing (set by runner)
    started_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def add_error(self, stage: str, msg: str) -> None:
        entry = f"[{stage}] {msg}"
        self.errors.append(entry)
        logger.warning("pipeline_error", stage=stage, error=msg)

    def set_stage_stat(self, stage: str, key: str, value: Any) -> None:
        self.stats.setdefault(stage, {})[key] = value

    def increment_stat(self, stage: str, key: str, by: int = 1) -> None:
        self.stats.setdefault(stage, {}).setdefault(key, 0)
        self.stats[stage][key] += by


class PipelineStageBase(ABC):
    """
    Abstract base for all pipeline stages.

    Subclasses implement `process(ctx)`.
    `safe_run` wraps it with timing and error handling.
    """

    name: str = "unnamed"

    @abstractmethod
    async def process(self, ctx: PipelineContext) -> PipelineContext:
        ...

    async def safe_run(self, ctx: PipelineContext) -> PipelineContext:
        log = logger.bind(stage=self.name, run_id=ctx.run_id)
        log.info("stage_start")
        t0 = time.monotonic()

        try:
            ctx = await self.process(ctx)
        except Exception as exc:
            ctx.add_error(self.name, str(exc))
            log.error("stage_failed", error=str(exc), exc_info=True)
        finally:
            elapsed = round(time.monotonic() - t0, 2)
            ctx.set_stage_stat(self.name, "duration_s", elapsed)
            log.info(
                "stage_done",
                duration_s=elapsed,
                stats=ctx.stats.get(self.name, {}),
            )

        return ctx
