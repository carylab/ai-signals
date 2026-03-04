"""
Structured logging configuration using structlog.

In development  → colourised, human-readable console output
In production   → JSON lines, suitable for Datadog / Loki / CloudWatch

Usage anywhere in the codebase:
    import structlog
    logger = structlog.get_logger(__name__)
    logger.info("event_name", key=value, ...)
"""
from __future__ import annotations

import logging
import sys
from typing import Literal

import structlog


def configure_logging(
    level: str = "INFO",
    fmt: Literal["json", "console"] = "console",
) -> None:
    """
    Call once at application startup before any logger is created.
    Subsequent calls are safe (idempotent via structlog's reset).
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    # ── Shared processors (run for every log record) ─────────────────────────
    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
    ]

    if fmt == "json":
        # Production: machine-readable JSON
        shared_processors.append(structlog.processors.dict_tracebacks)
        renderer = structlog.processors.JSONRenderer()
    else:
        # Development: colourised key=value output
        shared_processors.append(structlog.dev.set_exc_info)
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processor=renderer,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)

    # Quiet noisy third-party loggers
    for noisy in ("httpx", "httpcore", "feedparser", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_request_logger(request_id: str, path: str) -> structlog.stdlib.BoundLogger:
    """Return a logger pre-bound with HTTP request context."""
    return structlog.get_logger().bind(request_id=request_id, path=path)
