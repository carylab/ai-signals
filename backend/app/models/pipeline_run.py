"""
PipelineRun — audit log for each daily pipeline execution.
Tracks stage-by-stage statistics and error counts.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RunStatus:
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL = "partial"   # completed with some stage errors
    FAILED = "failed"


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    # UUID generated at run start

    date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    # target date for this run, "YYYY-MM-DD"

    status: Mapped[str] = mapped_column(
        String(20), default=RunStatus.RUNNING, nullable=False
    )

    # Timing
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_s: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Article counts
    articles_collected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    articles_after_dedup: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    articles_analyzed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    articles_published: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Cost tracking
    llm_input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    llm_output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    llm_cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Per-stage JSON stats and errors
    stage_stats: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # JSON: {"collect": {"fetched": 120, "errors": 2}, "summarize": {...}}

    error_log: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # JSON array of error strings

    def __repr__(self) -> str:
        return (
            f"<PipelineRun run_id={self.run_id!r} "
            f"date={self.date!r} status={self.status!r}>"
        )
