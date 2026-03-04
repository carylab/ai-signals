#!/usr/bin/env python3
"""
Standalone pipeline worker.

Runs the AI Signals pipeline on a cron schedule without needing the FastAPI
server to be running.  Suitable for:
  - Dedicated worker containers (Docker / Fly.io)
  - GitHub Actions or cron-based CI pipelines
  - Local development runs: `python scripts/run_worker.py`

Usage:
    # Start the scheduler (runs until killed):
    python scripts/run_worker.py

    # Run once now for a specific date and exit:
    python scripts/run_worker.py --run-now --date 2026-03-04

    # Run once for today and exit:
    python scripts/run_worker.py --run-now

Environment variables (same as the web server .env):
    DATABASE_URL, LLM_PROVIDER, OPENAI_API_KEY, etc.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import signal
import sys
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────
# Allow running from repo root without installing the package.
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

# ── Bootstrap ─────────────────────────────────────────────────────────────────

def _bootstrap() -> None:
    """Load .env and configure logging before any app imports."""
    # Load .env early so pydantic-settings picks it up
    env_file = REPO_ROOT / "backend" / ".env"
    if env_file.exists():
        from dotenv import load_dotenv
        load_dotenv(env_file)

    from app.core.logging import configure_logging
    from app.config import settings
    configure_logging(level=settings.log_level, fmt=settings.log_format)


# ── Run-once mode ─────────────────────────────────────────────────────────────

async def run_once(target_date: str | None = None) -> int:
    """Run the pipeline once and exit with 0 on success, 1 on failure."""
    import structlog
    from app.config import settings
    from app.core.database import init_db, create_all_tables
    from app.scheduler.retry import run_with_retry

    logger = structlog.get_logger("worker")

    # Ensure data directories
    os.makedirs("./data/db", exist_ok=True)
    os.makedirs(settings.export_dir, exist_ok=True)

    init_db(settings.database_url)
    await create_all_tables()

    logger.info("worker_run_once", date=target_date or "today")

    try:
        from app.scheduler.worker import _execute_pipeline
        await run_with_retry(_execute_pipeline, target_date)
        logger.info("worker_run_once_success")
        return 0
    except Exception as exc:
        logger.error("worker_run_once_failed", error=str(exc))
        return 1


# ── Daemon mode ───────────────────────────────────────────────────────────────

async def run_daemon() -> None:
    """Start the scheduler and run until SIGTERM / SIGINT."""
    import structlog
    from app.config import settings
    from app.core.database import init_db, create_all_tables
    from app.scheduler.worker import start_scheduler, stop_scheduler, scheduler_status

    logger = structlog.get_logger("worker")

    # Ensure data directories
    os.makedirs("./data/db", exist_ok=True)
    os.makedirs(settings.export_dir, exist_ok=True)

    init_db(settings.database_url)
    await create_all_tables()

    await start_scheduler()
    status = scheduler_status()
    logger.info(
        "worker_daemon_started",
        cron=status["cron"],
        next_run=status["next_run_at"],
    )

    # Block until signal
    stop_event = asyncio.Event()

    def _handle_signal(*_):
        logger.info("worker_shutdown_signal")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, _handle_signal)
        except NotImplementedError:
            # Windows
            signal.signal(sig, _handle_signal)

    await stop_event.wait()
    await stop_scheduler()
    logger.info("worker_daemon_stopped")


# ── CLI ───────────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="AI Signals pipeline worker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--run-now",
        action="store_true",
        help="Run the pipeline once immediately and exit",
    )
    p.add_argument(
        "--date",
        metavar="YYYY-MM-DD",
        default=None,
        help="Target date for --run-now (default: today)",
    )
    return p.parse_args()


def main() -> None:
    _bootstrap()
    args = _parse_args()

    if args.run_now:
        exit_code = asyncio.run(run_once(args.date))
        sys.exit(exit_code)
    else:
        asyncio.run(run_daemon())


if __name__ == "__main__":
    main()
