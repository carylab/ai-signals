"""
Shared async HTTP client with retry, timeout and rate-limit handling.

All crawler modules use this instead of creating their own httpx clients,
so connection pools are reused and settings are consistent.
"""
from __future__ import annotations

import asyncio
from typing import Optional

import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings
from app.core.exceptions import CrawlerError, CrawlerTimeoutError

logger = structlog.get_logger(__name__)

# Module-level singleton — created lazily on first use
_client: Optional[httpx.AsyncClient] = None


def _get_default_headers() -> dict[str, str]:
    return {
        "User-Agent": settings.crawler_user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    }


def get_http_client() -> httpx.AsyncClient:
    """Return the module-level async HTTP client, creating it if necessary."""
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=10.0,
                read=float(settings.crawler_request_timeout_s),
                write=10.0,
                pool=5.0,
            ),
            headers=_get_default_headers(),
            follow_redirects=True,
            max_redirects=5,
            http2=False,   # keep it simple; many sites don't need h2
            limits=httpx.Limits(
                max_connections=50,
                max_keepalive_connections=20,
                keepalive_expiry=30,
            ),
        )
    return _client


async def close_http_client() -> None:
    """Call at application shutdown."""
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
        _client = None


async def fetch_url(
    url: str,
    *,
    headers: Optional[dict] = None,
    timeout: Optional[float] = None,
    retries: int = 2,
) -> httpx.Response:
    """
    Fetch a URL with automatic retries on transient errors.

    Raises:
        CrawlerTimeoutError — request timed out after all retries
        CrawlerError        — non-transient HTTP error or connection failure
    """
    client = get_http_client()
    extra_headers = headers or {}

    attempt = 0
    last_exc: Optional[Exception] = None

    while attempt <= retries:
        attempt += 1
        try:
            response = await client.get(
                url,
                headers=extra_headers,
                timeout=timeout or float(settings.crawler_request_timeout_s),
            )
            response.raise_for_status()
            logger.debug(
                "fetch_ok",
                url=url,
                status=response.status_code,
                attempt=attempt,
            )
            return response

        except httpx.TimeoutException as exc:
            last_exc = exc
            logger.warning("fetch_timeout", url=url, attempt=attempt)
            if attempt <= retries:
                await asyncio.sleep(2 ** attempt)  # 2s, 4s backoff

        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            # Don't retry 4xx (client errors)
            if 400 <= status < 500:
                raise CrawlerError(url, f"HTTP {status}") from exc
            last_exc = exc
            logger.warning("fetch_http_error", url=url, status=status, attempt=attempt)
            if attempt <= retries:
                await asyncio.sleep(2 ** attempt)

        except httpx.RequestError as exc:
            last_exc = exc
            logger.warning("fetch_request_error", url=url, error=str(exc), attempt=attempt)
            if attempt <= retries:
                await asyncio.sleep(2 ** attempt)

    # All retries exhausted
    if isinstance(last_exc, httpx.TimeoutException):
        raise CrawlerTimeoutError(url) from last_exc
    raise CrawlerError(url, str(last_exc)) from last_exc
