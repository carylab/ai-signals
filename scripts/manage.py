#!/usr/bin/env python3
"""
AI Signals management CLI.

Provides operational commands without needing the web server running.

Usage:
    python scripts/manage.py pipeline run
    python scripts/manage.py pipeline run --date 2026-03-01
    python scripts/manage.py pipeline backfill --from 2026-02-01 --to 2026-02-28
    python scripts/manage.py pipeline status
    python scripts/manage.py db migrate
    python scripts/manage.py db seed
    python scripts/manage.py sources list
    python scripts/manage.py sources enable arxiv
    python scripts/manage.py sources disable arxiv
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import date, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))


def _bootstrap() -> None:
    env_file = REPO_ROOT / "backend" / ".env"
    if env_file.exists():
        from dotenv import load_dotenv
        load_dotenv(env_file)
    from app.core.logging import configure_logging
    from app.config import settings
    configure_logging(level=settings.log_level, fmt="console")


# ── Pipeline commands ─────────────────────────────────────────────────────────

async def cmd_pipeline_run(target_date: str | None) -> int:
    import structlog
    from app.config import settings
    from app.core.database import init_db, create_all_tables
    from app.scheduler.worker import _execute_pipeline
    from app.scheduler.retry import run_with_retry
    import os

    logger = structlog.get_logger("manage")
    os.makedirs("./data/db", exist_ok=True)
    os.makedirs(settings.export_dir, exist_ok=True)
    init_db(settings.database_url)
    await create_all_tables()

    logger.info("cmd_pipeline_run", date=target_date or "today")
    try:
        await run_with_retry(_execute_pipeline, target_date)
        logger.info("cmd_pipeline_run_ok")
        return 0
    except Exception as exc:
        logger.error("cmd_pipeline_run_failed", error=str(exc))
        return 1


async def cmd_pipeline_backfill(from_date: str, to_date: str) -> int:
    """Run pipeline for every day in [from_date, to_date]."""
    import structlog
    from app.config import settings
    from app.core.database import init_db, create_all_tables
    from app.scheduler.worker import _execute_pipeline
    from app.scheduler.retry import run_with_retry
    import os

    logger = structlog.get_logger("manage")
    os.makedirs("./data/db", exist_ok=True)
    os.makedirs(settings.export_dir, exist_ok=True)
    init_db(settings.database_url)
    await create_all_tables()

    start = date.fromisoformat(from_date)
    end   = date.fromisoformat(to_date)
    if start > end:
        print(f"ERROR: --from {from_date} is after --to {to_date}", file=sys.stderr)
        return 1

    current = start
    errors = []
    while current <= end:
        d = current.isoformat()
        logger.info("backfill_day", date=d)
        try:
            await run_with_retry(_execute_pipeline, d, max_attempts=2, base_delay=30.0)
            logger.info("backfill_day_ok", date=d)
        except Exception as exc:
            logger.error("backfill_day_failed", date=d, error=str(exc))
            errors.append(d)
        current += timedelta(days=1)

    if errors:
        print(f"Backfill completed with {len(errors)} failures: {errors}")
        return 1

    print(f"Backfill complete: {(end - start).days + 1} days processed.")
    return 0


async def cmd_pipeline_status() -> int:
    """Print recent pipeline run history from the DB."""
    from app.config import settings
    from app.core.database import init_db
    from sqlalchemy import select, desc
    from app.models.pipeline_run import PipelineRun
    import os

    os.makedirs("./data/db", exist_ok=True)
    init_db(settings.database_url)

    from app.core.database import get_sessionmaker
    async_session = get_sessionmaker()
    async with async_session() as session:
        rows = (
            await session.execute(
                select(PipelineRun).order_by(desc(PipelineRun.started_at)).limit(10)
            )
        ).scalars().all()

    if not rows:
        print("No pipeline runs found.")
        return 0

    header = f"{'DATE':<12} {'STATUS':<10} {'COLLECTED':>10} {'PUBLISHED':>10} {'DURATION':>10} {'ERRORS':>7}"
    print(header)
    print("-" * len(header))
    for r in rows:
        print(
            f"{r.date:<12} {r.status:<10} "
            f"{(r.articles_collected or 0):>10} {(r.articles_published or 0):>10} "
            f"{(r.duration_s or 0):>9.1f}s {len(r.error_log or '[]') - 2:>7}"
        )
    return 0


# ── DB commands ───────────────────────────────────────────────────────────────

async def cmd_db_migrate() -> int:
    """Run Alembic migrations (equivalent to `alembic upgrade head`)."""
    import subprocess
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=str(REPO_ROOT / "backend"),
    )
    return result.returncode


async def cmd_db_seed() -> int:
    """Seed news sources."""
    import subprocess
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "seed_sources.py")],
        cwd=str(REPO_ROOT / "backend"),
    )
    return result.returncode


# ── Sources commands ──────────────────────────────────────────────────────────

async def cmd_sources_list() -> int:
    from app.config import settings
    from app.core.database import init_db, get_sessionmaker
    from sqlalchemy import select
    from app.models.source import NewsSource
    import os

    os.makedirs("./data/db", exist_ok=True)
    init_db(settings.database_url)

    async_session = get_sessionmaker()
    async with async_session() as session:
        sources = (await session.execute(select(NewsSource).order_by(NewsSource.priority))).scalars().all()

    if not sources:
        print("No sources found. Run: python scripts/manage.py db seed")
        return 0

    header = f"{'SLUG':<30} {'TYPE':<8} {'ACTIVE':<7} {'PRIORITY':>8} {'HEALTH':>8}"
    print(header)
    print("-" * len(header))
    for s in sources:
        print(
            f"{s.slug:<30} {s.source_type:<8} {'yes' if s.is_active else 'no':<7} "
            f"{s.priority:>8} {(s.health_score or 1.0):>8.2f}"
        )
    return 0


async def _toggle_source(slug: str, active: bool) -> int:
    from app.config import settings
    from app.core.database import init_db, get_sessionmaker
    from sqlalchemy import select
    from app.models.source import NewsSource
    import os

    os.makedirs("./data/db", exist_ok=True)
    init_db(settings.database_url)

    async_session = get_sessionmaker()
    async with async_session() as session:
        source = (
            await session.execute(select(NewsSource).where(NewsSource.slug == slug))
        ).scalar_one_or_none()
        if not source:
            print(f"Source '{slug}' not found.", file=sys.stderr)
            return 1
        source.is_active = active
        await session.commit()

    state = "enabled" if active else "disabled"
    print(f"Source '{slug}' {state}.")
    return 0


# ── CLI parser ────────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="AI Signals management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = p.add_subparsers(dest="group", required=True)

    # pipeline
    pipe = sub.add_parser("pipeline", help="Pipeline operations")
    pipe_sub = pipe.add_subparsers(dest="cmd", required=True)

    run_p = pipe_sub.add_parser("run", help="Run pipeline once")
    run_p.add_argument("--date", metavar="YYYY-MM-DD", default=None)

    bf = pipe_sub.add_parser("backfill", help="Run pipeline over a date range")
    bf.add_argument("--from", dest="from_date", required=True, metavar="YYYY-MM-DD")
    bf.add_argument("--to",   dest="to_date",   required=True, metavar="YYYY-MM-DD")

    pipe_sub.add_parser("status", help="Show recent run history")

    # db
    db = sub.add_parser("db", help="Database operations")
    db_sub = db.add_subparsers(dest="cmd", required=True)
    db_sub.add_parser("migrate", help="Run Alembic migrations")
    db_sub.add_parser("seed",    help="Seed news sources")

    # sources
    src = sub.add_parser("sources", help="Manage news sources")
    src_sub = src.add_subparsers(dest="cmd", required=True)
    src_sub.add_parser("list", help="List all sources")

    en = src_sub.add_parser("enable", help="Enable a source")
    en.add_argument("slug")

    dis = src_sub.add_parser("disable", help="Disable a source")
    dis.add_argument("slug")

    return p


async def _dispatch(args: argparse.Namespace) -> int:
    if args.group == "pipeline":
        if args.cmd == "run":
            return await cmd_pipeline_run(args.date)
        elif args.cmd == "backfill":
            return await cmd_pipeline_backfill(args.from_date, args.to_date)
        elif args.cmd == "status":
            return await cmd_pipeline_status()

    elif args.group == "db":
        if args.cmd == "migrate":
            return await cmd_db_migrate()
        elif args.cmd == "seed":
            return await cmd_db_seed()

    elif args.group == "sources":
        if args.cmd == "list":
            return await cmd_sources_list()
        elif args.cmd == "enable":
            return await _toggle_source(args.slug, True)
        elif args.cmd == "disable":
            return await _toggle_source(args.slug, False)

    return 1


def main() -> None:
    _bootstrap()
    parser = _build_parser()
    args = parser.parse_args()
    exit_code = asyncio.run(_dispatch(args))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
