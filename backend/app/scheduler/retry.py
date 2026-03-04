"""
Retry helper for the pipeline worker.

Wraps _execute_pipeline with exponential back-off so transient failures
(network blips, LLM rate limits) don't abort the whole daily run.

Retry policy:
  - 3 attempts total (1 initial + 2 retries)
  - Exponential back-off: 60s → 120s between attempts
  - Does NOT retry on KeyboardInterrupt or SystemExit
  - Re-raises after exhausting all attempts so the caller can log failure
"""
from __future__ import annotations

import asyncio
from typing import Callable, Awaitable, TypeVar

import structlog

logger = structlog.get_logger(__name__)

T = TypeVar("T")

_MAX_ATTEMPTS = 3
_BASE_DELAY_S = 60.0   # 1 minute between retries
_BACKOFF_FACTOR = 2.0


async def run_with_retry(
    fn: Callable[..., Awaitable[T]],
    *args,
    max_attempts: int = _MAX_ATTEMPTS,
    base_delay: float = _BASE_DELAY_S,
    **kwargs,
) -> T:
    """
    Call ``fn(*args, **kwargs)`` up to ``max_attempts`` times.

    Each failure waits ``base_delay * 2^attempt`` seconds before retrying.
    """
    last_exc: BaseException = RuntimeError("No attempts made")

    for attempt in range(max_attempts):
        try:
            return await fn(*args, **kwargs)
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as exc:
            last_exc = exc
            if attempt < max_attempts - 1:
                delay = base_delay * (_BACKOFF_FACTOR ** attempt)
                logger.warning(
                    "pipeline_retry",
                    attempt=attempt + 1,
                    max_attempts=max_attempts,
                    delay_s=delay,
                    error=str(exc),
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    "pipeline_failed_all_attempts",
                    max_attempts=max_attempts,
                    error=str(exc),
                )

    raise last_exc
