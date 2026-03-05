"""
APScheduler-based background scheduler.

Responsibilities:
  - Run the AI pipeline on the configured cron schedule
  - Expose start/stop coroutines called by the FastAPI lifespan
  - Prevent overlapping runs via an asyncio.Lock
  - Surface next-run time and last-run status for the /stats endpoint

The scheduler lives inside the FastAPI process.  For higher-reliability
deployments the standalone worker (scripts/run_worker.py) can take over.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Optional

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings
from app.scheduler.retry import run_with_retry
from app.scheduler.health import health_monitor

logger = structlog.get_logger(__name__)

# ── Module-level state ────────────────────────────────────────────────────────

_scheduler: Optional[AsyncIOScheduler] = None
_run_lock: asyncio.Lock = asyncio.Lock()

_last_run_at:     Optional[datetime] = None
_last_run_status: Optional[str]      = None  # "success" | "partial" | "failed"
_next_run_at:     Optional[datetime] = None


# ── Public API ────────────────────────────────────────────────────────────────

async def start_scheduler() -> None:
    """Start the APScheduler.  Called from the FastAPI lifespan."""
    global _scheduler

    _scheduler = AsyncIOScheduler(timezone="UTC")
    _scheduler.add_job(
        _pipeline_job,
        trigger=CronTrigger.from_crontab(settings.pipeline_cron, timezone="UTC"),
        id="daily_pipeline",
        name="Daily AI pipeline",
        max_instances=1,           # APScheduler-level guard (belt-and-suspenders)
        misfire_grace_time=3600,   # allow up to 1h late start
        replace_existing=True,
    )
    _scheduler.start()
    _refresh_next_run()
    logger.info("scheduler_started", cron=settings.pipeline_cron, next_run=_next_run_at)


async def stop_scheduler() -> None:
    """Gracefully stop the scheduler.  Called from the FastAPI lifespan."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("scheduler_stopped")
    _scheduler = None


async def trigger_now(target_date: Optional[str] = None) -> str:
    """
    Trigger a pipeline run immediately (used by the /pipeline/trigger endpoint).

    Returns the run_id of the initiated run, or raises RuntimeError if a run
    is already in progress.
    """
    if _run_lock.locked():
        raise RuntimeError("A pipeline run is already in progress.")
    # Schedule a one-shot job; the lock prevents overlap with the cron job.
    asyncio.create_task(_pipeline_job(target_date=target_date))
    return "triggered"


def scheduler_status() -> dict:
    """Return a dict suitable for the /stats endpoint."""
    return {
        "enabled":          settings.pipeline_enabled,
        "cron":             settings.pipeline_cron,
        "running":          _run_lock.locked(),
        "last_run_at":      _last_run_at.isoformat() if _last_run_at else None,
        "last_run_status":  _last_run_status,
        "next_run_at":      _next_run_at.isoformat() if _next_run_at else None,
        "health":           health_monitor.summary(),
    }


# ── Internal job ─────────────────────────────────────────────────────────────

async def _pipeline_job(target_date: Optional[str] = None) -> None:
    """
    Core pipeline job.

    Acquires the run lock so only one pipeline runs at a time regardless of
    whether it was triggered by the cron, the API, or the standalone worker.
    """
    global _last_run_at, _last_run_status, _next_run_at

    if _run_lock.locked():
        logger.warning("pipeline_skipped_already_running")
        return

    run_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc)

    async with _run_lock:
        _last_run_at = started_at
        _last_run_status = "running"
        log = logger.bind(run_id=run_id, target_date=target_date or "today")
        log.info("pipeline_job_start")

        status = "failed"
        ctx = None
        try:
            ctx = await run_with_retry(
                _execute_pipeline,
                target_date,
            )
            status = "success"
            log.info("pipeline_job_success")
        except Exception as exc:
            status = "failed"
            log.exception("pipeline_job_failed", error=str(exc))
        finally:
            _last_run_status = status
            _refresh_next_run()

            # Record in health monitor
            duration_s = (datetime.now(timezone.utc) - started_at).total_seconds()
            health_monitor.record(
                run_id=run_id,
                started_at=started_at,
                status=status,
                duration_s=round(duration_s, 1),
                collected=ctx.stats.get("collect", {}).get("articles_fetched", 0) if ctx else 0,
                published=ctx.stats.get("store", {}).get("published", 0) if ctx else 0,
                errors=len(ctx.errors) if ctx else 1,
            )


async def _execute_pipeline(target_date: Optional[str]):
    """Build all dependencies and run the pipeline. Returns PipelineContext."""
    from app.core.database import get_sessionmaker
    from app.services.llm.factory import create_llm_client

    llm_client = create_llm_client(
        provider=settings.llm_provider,
        model=settings.llm_model,
        api_key=settings.active_llm_key or "",
    )

    async_session = get_sessionmaker()
    async with async_session() as session:
        from app.pipeline.runner import PipelineRunner
        runner = PipelineRunner(
            session=session,
            llm_client=llm_client,
            export_dir=settings.export_dir,
        )
        return await runner.run(target_date=target_date)


def _refresh_next_run() -> None:
    global _next_run_at
    if _scheduler and _scheduler.running:
        job = _scheduler.get_job("daily_pipeline")
        if job and job.next_run_time:
            _next_run_at = job.next_run_time
