"""
FastAPI application entrypoint.

Startup sequence:
  1. Configure structured logging
  2. Initialise DB engine and create tables (dev) / run migrations check (prod)
  3. Mount API router
  4. Register exception handlers
  5. Start background scheduler

Lifespan context manager handles clean startup and shutdown.
"""
from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.logging import configure_logging
from app.core.database import init_db, create_all_tables
from app.core.exceptions import AISignalsError, NotFoundError

logger = structlog.get_logger(__name__)

_API_DESCRIPTION = """
## AI Signals API

Automated AI industry intelligence platform.

### Features
- **News** — curated, scored AI news articles
- **Briefs** — daily AI intelligence summaries
- **Trends** — real-time trending topics, companies, and models
- **Search** — full-text search across all articles
- **RSS** — machine-readable feeds for all content types

### Scoring
Every article receives four sub-scores:
- `importance_score` — source authority + content signals
- `freshness_score`  — exponential decay (24h half-life)
- `trend_score`      — alignment with trending topics
- `discussion_score` — cluster coverage breadth

`final_score = importance×0.40 + freshness×0.30 + trend×0.20 + discussion×0.10`
"""

_OPENAPI_TAGS = [
    {"name": "News",      "description": "Article listing, detail, and filtering"},
    {"name": "Briefs",    "description": "Daily AI intelligence briefs"},
    {"name": "Trends",    "description": "Trending topics, companies, and models"},
    {"name": "Topics",    "description": "Tag/topic pages with article lists"},
    {"name": "Companies", "description": "AI company profiles"},
    {"name": "Search",    "description": "Full-text article search"},
    {"name": "RSS",       "description": "RSS 2.0 feeds"},
    {"name": "Stats",     "description": "Platform statistics"},
    {"name": "Pipeline",  "description": "Internal ops — pipeline control and monitoring"},
]


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # ── Startup ──────────────────────────────────────────────────────────────
    configure_logging(level=settings.log_level, fmt=settings.log_format)
    logger.info(
        "startup",
        app=settings.app_name,
        env=settings.app_env,
        llm_provider=settings.llm_provider,
        llm_model=settings.llm_model,
    )

    # Ensure data directories exist
    import os
    os.makedirs("./data/db", exist_ok=True)
    os.makedirs(settings.export_dir, exist_ok=True)

    # Initialise DB
    init_db(settings.database_url)

    if settings.app_env in ("development", "test"):
        # Dev: auto-create tables without Alembic
        await create_all_tables()
        logger.info("db_tables_created")
    else:
        # Production: tables must exist via `alembic upgrade head`
        logger.info("db_production_mode_no_autocreate")

    # Start scheduler
    if settings.pipeline_enabled and settings.app_env != "test":
        from app.scheduler.worker import start_scheduler
        await start_scheduler()
        logger.info("scheduler_started", cron=settings.pipeline_cron)

    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    if settings.pipeline_enabled and settings.app_env != "test":
        from app.scheduler.worker import stop_scheduler
        await stop_scheduler()

    from app.core.database import get_engine
    await get_engine().dispose()
    logger.info("shutdown_complete")


# ── App factory ───────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Signals API",
        description=_API_DESCRIPTION,
        version="1.0.0",
        contact={"name": "AI Signals", "url": "https://aisignals.io"},
        license_info={"name": "MIT"},
        docs_url="/api/docs" if not settings.is_production else None,
        redoc_url="/api/redoc" if not settings.is_production else None,
        openapi_url="/api/openapi.json" if not settings.is_production else None,
        openapi_tags=_OPENAPI_TAGS,
        lifespan=lifespan,
    )

    _add_middleware(app)
    _add_exception_handlers(app)
    _mount_routers(app)

    return app


# ── Middleware ────────────────────────────────────────────────────────────────

def _add_middleware(app: FastAPI) -> None:
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )

    # Request ID + timing middleware
    @app.middleware("http")
    async def request_context_middleware(
        request: Request, call_next
    ) -> Response:
        request_id = str(uuid.uuid4())[:8]
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        t0 = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - t0) * 1000, 1)

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{duration_ms}ms"

        logger.info(
            "http_request",
            status=response.status_code,
            duration_ms=duration_ms,
        )
        return response


# ── Exception handlers ────────────────────────────────────────────────────────

def _add_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AISignalsError)
    async def domain_error_handler(
        request: Request, exc: AISignalsError
    ) -> JSONResponse:
        logger.warning(
            "domain_error",
            error_type=type(exc).__name__,
            message=exc.message,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=exc.http_status,
            content=exc.to_dict(),
        )

    @app.exception_handler(404)
    async def not_found_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={"error": "NotFound", "message": f"Path {request.url.path!r} not found."},
        )

    @app.exception_handler(500)
    async def internal_error_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.error("unhandled_error", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "InternalServerError", "message": "An unexpected error occurred."},
        )


# ── Routers ───────────────────────────────────────────────────────────────────

def _mount_routers(app: FastAPI) -> None:
    from app.api.router import api_router
    app.include_router(api_router, prefix="/api")

    # Health check (outside /api so load balancers can hit it without auth)
    @app.get("/health", tags=["ops"], include_in_schema=False)
    async def health() -> dict:
        return {"status": "ok", "app": settings.app_name, "env": settings.app_env}

    @app.get("/", include_in_schema=False)
    async def root() -> dict:
        return {"message": f"Welcome to {settings.app_name} API", "docs": "/api/docs"}


# ── WSGI entrypoint ───────────────────────────────────────────────────────────

app = create_app()
