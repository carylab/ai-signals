"""
Abstract LLM client interface.

Every provider (OpenAI, Anthropic, DeepSeek, OpenRouter) implements
this interface.  The rest of the codebase only depends on BaseLLMClient,
making provider switching a single config change.

Key design decisions:
  - complete()       → raw string response
  - complete_json()  → parsed dict (client handles retry on bad JSON)
  - All methods are async
  - Token usage and cost are tracked in LLMResponse
  - Retries live here (via tenacity), not in callers
"""
from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class LLMResponse:
    """Normalised response from any LLM provider."""
    content: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    # Raw provider response stored for debugging
    raw: Optional[dict] = field(default=None, repr=False)


class BaseLLMClient(ABC):
    """
    Abstract base for all LLM provider clients.

    Subclasses must implement:
        _call(system, user, temperature, max_tokens) → LLMResponse

    complete() and complete_json() are implemented here with
    shared retry / parsing logic.
    """

    model: str = ""
    provider: str = ""

    # Cost per 1K tokens (input, output) in USD — override in subclass
    _cost_per_1k_input: float = 0.0
    _cost_per_1k_output: float = 0.0

    @abstractmethod
    async def _call(
        self,
        system: str,
        user: str,
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse:
        """Provider-specific API call. Must be implemented by each subclass."""
        ...

    async def complete(
        self,
        system: str,
        user: str,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        """
        Call the LLM and return a raw string response.
        Includes retry logic via _call_with_retry().
        """
        response = await self._call_with_retry(
            system=system,
            user=user,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        logger.debug(
            "llm_complete",
            provider=self.provider,
            model=self.model,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            cost_usd=response.cost_usd,
        )
        return response

    async def complete_json(
        self,
        system: str,
        user: str,
        temperature: float = 0.1,
        max_tokens: int = 1024,
        max_parse_retries: int = 2,
    ) -> dict:
        """
        Call the LLM and parse the response as JSON.

        Retries up to max_parse_retries times if the response is not
        valid JSON, appending a correction instruction to the prompt.

        Returns the parsed dict directly (not LLMResponse) for ergonomics.
        """
        # Tell the model to respond with pure JSON
        json_system = (
            system
            + "\n\nIMPORTANT: Respond with valid JSON only. "
            "No markdown code fences, no explanation text."
        )

        current_user = user
        last_content = ""

        for attempt in range(max_parse_retries + 1):
            response = await self._call_with_retry(
                system=json_system,
                user=current_user,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            last_content = response.content

            parsed = _try_parse_json(last_content)
            if parsed is not None:
                # Attach token metadata so callers can accumulate costs
                parsed["_input_tokens"] = response.input_tokens
                parsed["_output_tokens"] = response.output_tokens
                parsed["_cost_usd"] = response.cost_usd
                return parsed

            logger.warning(
                "llm_json_parse_failed",
                attempt=attempt + 1,
                provider=self.provider,
                preview=last_content[:100],
            )

            if attempt < max_parse_retries:
                # Ask the model to fix its output
                current_user = (
                    f"{user}\n\nYour previous response was not valid JSON:\n"
                    f"```\n{last_content[:300]}\n```\n"
                    "Please respond with ONLY a valid JSON object."
                )

        # All parse retries exhausted — return empty dict so pipeline continues
        from app.core.exceptions import LLMParseError
        raise LLMParseError(
            provider=self.provider,
            message=f"Failed to parse JSON after {max_parse_retries + 1} attempts.",
            detail={"preview": last_content[:200]},
        )

    async def _call_with_retry(
        self,
        system: str,
        user: str,
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse:
        """Wrap _call() with exponential-backoff retry via tenacity."""
        from tenacity import (
            AsyncRetrying,
            retry_if_exception_type,
            stop_after_attempt,
            wait_exponential,
        )
        from app.core.exceptions import LLMError, RateLimitError
        from app.config import settings

        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(settings.llm_max_retries),
            wait=wait_exponential(multiplier=1, min=2, max=30),
            retry=retry_if_exception_type((LLMError, RateLimitError)),
            reraise=True,
        ):
            with attempt:
                return await self._call(system, user, temperature, max_tokens)

        # Should never reach here (reraise=True above)
        raise RuntimeError("LLM retry loop exited unexpectedly")

    def _compute_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Compute USD cost from token counts and per-model rates."""
        return (
            input_tokens / 1000 * self._cost_per_1k_input
            + output_tokens / 1000 * self._cost_per_1k_output
        )


# ---------------------------------------------------------------------------
# JSON parsing helpers
# ---------------------------------------------------------------------------

def _try_parse_json(text: str) -> Optional[dict]:
    """
    Attempt to extract a JSON object from LLM output.
    Handles:
      - Pure JSON response
      - JSON wrapped in ```json ... ``` fences
      - JSON with leading/trailing prose
    """
    text = text.strip()

    # 1. Direct parse
    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass

    # 2. Strip markdown code fences
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        try:
            result = json.loads(fenced.group(1))
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass

    # 3. Find first {...} block in the string
    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        try:
            result = json.loads(brace_match.group())
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass

    return None
