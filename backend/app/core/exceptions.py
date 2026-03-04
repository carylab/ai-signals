"""
Domain exceptions for AI Signals.

Hierarchy:
    AISignalsError (base)
    ├── NotFoundError          → HTTP 404
    ├── ValidationError        → HTTP 422
    ├── RateLimitError         → HTTP 429
    ├── LLMError               → HTTP 502
    │   └── LLMTimeoutError
    ├── CrawlerError           → HTTP 502
    │   └── CrawlerTimeoutError
    └── PipelineError          → HTTP 500
"""
from __future__ import annotations

from typing import Any, Optional


class AISignalsError(Exception):
    """Base exception for all domain errors."""

    http_status: int = 500
    default_message: str = "An unexpected error occurred."

    def __init__(
        self,
        message: Optional[str] = None,
        detail: Optional[Any] = None,
    ) -> None:
        self.message = message or self.default_message
        self.detail = detail
        super().__init__(self.message)

    def to_dict(self) -> dict:
        d: dict = {"error": self.__class__.__name__, "message": self.message}
        if self.detail is not None:
            d["detail"] = self.detail
        return d


# ── HTTP 404 ─────────────────────────────────────────────────────────────────

class NotFoundError(AISignalsError):
    http_status = 404
    default_message = "Resource not found."

    def __init__(self, resource: str, identifier: Any) -> None:
        super().__init__(
            message=f"{resource} not found: {identifier!r}",
            detail={"resource": resource, "identifier": str(identifier)},
        )


# ── HTTP 422 ─────────────────────────────────────────────────────────────────

class ValidationError(AISignalsError):
    http_status = 422
    default_message = "Validation failed."


# ── HTTP 429 ─────────────────────────────────────────────────────────────────

class RateLimitError(AISignalsError):
    http_status = 429
    default_message = "Rate limit exceeded. Please try again later."

    def __init__(self, provider: str, retry_after_s: Optional[int] = None) -> None:
        super().__init__(
            message=f"Rate limit hit on {provider}.",
            detail={"provider": provider, "retry_after_s": retry_after_s},
        )
        self.retry_after_s = retry_after_s


# ── LLM errors ───────────────────────────────────────────────────────────────

class LLMError(AISignalsError):
    http_status = 502
    default_message = "LLM request failed."

    def __init__(
        self,
        provider: str,
        message: Optional[str] = None,
        detail: Optional[Any] = None,
    ) -> None:
        super().__init__(
            message=message or f"LLM error from provider {provider!r}.",
            detail=detail,
        )
        self.provider = provider


class LLMTimeoutError(LLMError):
    default_message = "LLM request timed out."


class LLMParseError(LLMError):
    """Raised when the LLM response cannot be parsed as expected JSON."""
    default_message = "Failed to parse LLM response."


# ── Crawler errors ────────────────────────────────────────────────────────────

class CrawlerError(AISignalsError):
    http_status = 502
    default_message = "Crawler request failed."

    def __init__(self, url: str, message: Optional[str] = None) -> None:
        super().__init__(
            message=message or f"Failed to fetch {url!r}.",
            detail={"url": url},
        )
        self.url = url


class CrawlerTimeoutError(CrawlerError):
    default_message = "Crawler request timed out."


# ── Pipeline errors ───────────────────────────────────────────────────────────

class PipelineError(AISignalsError):
    http_status = 500
    default_message = "Pipeline execution failed."

    def __init__(self, stage: str, message: Optional[str] = None) -> None:
        super().__init__(
            message=message or f"Pipeline stage {stage!r} failed.",
            detail={"stage": stage},
        )
        self.stage = stage
