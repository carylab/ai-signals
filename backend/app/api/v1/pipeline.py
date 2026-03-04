"""
/api/v1/pipeline  — pipeline trigger, run history, and source management.
"""
from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import desc, select

from app.config import settings
from app.dependencies import DbSession
from app.models.pipeline_run import PipelineRun
from app.models.source import NewsSource
from app.schemas.api import PipelineRunDetail, PipelineRunSchema, SourceSchema
from app.schemas.common import PaginatedResponse

router = APIRouter()
logger = structlog.get_logger(__name__)


def _check_internal(x_internal_token: str = Header(default="")) -> None:
    """Lightweight internal-only guard. Replace with OAuth2 in production."""
    if settings.is_production and x_internal_token != settings.secret_key:
        raise HTTPException(status_code=403, detail="Forbidden")


# ── Trigger ───────────────────────────────────────────────────────────────────

@router.post("/trigger", dependencies=[Depends(_check_internal)])
async def trigger_pipeline(
    date: str = Query(default="", description="Target date YYYY-MM-DD (default: today)"),
) -> dict:
    """
    Manually trigger a full pipeline run via the scheduler.

    The run executes asynchronously in the background.
    Returns 409 if a run is already in progress.
    """
    from app.scheduler.worker import trigger_now

    target_date = date.strip() or None
    try:
        await trigger_now(target_date=target_date)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    logger.info("pipeline_triggered", date=target_date or "today")
    return {"status": "triggered", "date": target_date or "today"}


@router.get("/scheduler")
async def get_scheduler_status() -> dict:
    """Return scheduler state: cron, running flag, last/next run times."""
    try:
        from app.scheduler.worker import scheduler_status
        return scheduler_status()
    except Exception:
        return {"enabled": False, "error": "Scheduler not initialised"}


@router.post("/trends/refresh", dependencies=[Depends(_check_internal)])
async def refresh_trends(
    background_tasks: BackgroundTasks,
    date: str = Query(default=""),
) -> dict:
    """Re-run trend detection without running the full pipeline."""
    from app.services.trend.detector import TrendDetector
    from app.core.database import get_session as _gs

    target_date = date.strip() or None

    async def _run() -> None:
        async for session in _gs():
            detector = TrendDetector(session)
            await detector.run(target_date=target_date)

    background_tasks.add_task(_run)
    return {"status": "triggered", "date": target_date or "today"}


# ── Run history ───────────────────────────────────────────────────────────────

@router.get("/runs", response_model=PaginatedResponse[PipelineRunSchema])
async def list_runs(
    db: DbSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
) -> PaginatedResponse[PipelineRunSchema]:
    from sqlalchemy import func

    total = (
        await db.execute(select(func.count()).select_from(PipelineRun))
    ).scalar_one()

    runs = (
        await db.execute(
            select(PipelineRun)
            .order_by(desc(PipelineRun.started_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()

    return PaginatedResponse.build(
        items=[PipelineRunSchema.model_validate(r) for r in runs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/runs/{run_id}", response_model=PipelineRunDetail)
async def get_run(run_id: str, db: DbSession) -> PipelineRunDetail:
    run = await db.scalar(
        select(PipelineRun).where(PipelineRun.run_id == run_id)
    )
    if not run:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("PipelineRun", run_id)
    return PipelineRunDetail.model_validate(run)


# ── Source management ─────────────────────────────────────────────────────────

@router.get("/sources", response_model=list[SourceSchema])
async def list_sources(db: DbSession) -> list[SourceSchema]:
    """List all news sources with health status."""
    sources = (
        await db.execute(
            select(NewsSource).order_by(
                NewsSource.priority.asc(),
                NewsSource.name.asc(),
            )
        )
    ).scalars().all()
    return [SourceSchema.model_validate(s) for s in sources]


@router.patch(
    "/sources/{slug}/toggle",
    dependencies=[Depends(_check_internal)],
)
async def toggle_source(slug: str, db: DbSession) -> dict:
    """Enable or disable a news source."""
    source = await db.scalar(
        select(NewsSource).where(NewsSource.slug == slug)
    )
    if not source:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("NewsSource", slug)

    source.is_active = not source.is_active
    if source.is_active:
        source.consecutive_errors = 0
    await db.flush()

    logger.info("source_toggled", slug=slug, is_active=source.is_active)
    return {"slug": slug, "is_active": source.is_active}
