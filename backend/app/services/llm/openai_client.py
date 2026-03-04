"""
OpenAI provider client.

Supports:
  - gpt-4o-mini  (default, cost-efficient)
  - gpt-4o
  - gpt-4-turbo
  - o1-mini / o1-preview  (reasoning models — no system prompt)

Uses the official openai Python SDK (v1.x async client).
"""
from __future__ import annotations

from typing import Optional

import structlog
from openai import AsyncOpenAI, APIStatusError, APITimeoutError, RateLimitError as OAIRateLimit

from app.services.llm.base import BaseLLMClient, LLMResponse
from app.core.exceptions import LLMError, LLMTimeoutError, RateLimitError

logger = structlog.get_logger(__name__)

# Cost per 1K tokens (USD) — update when OpenAI changes pricing
_MODEL_COSTS: dict[str, tuple[float, float]] = {
    "gpt-4o":           (0.005,  0.015),
    "gpt-4o-mini":      (0.00015, 0.0006),
    "gpt-4-turbo":      (0.01,   0.03),
    "gpt-3.5-turbo":    (0.0005, 0.0015),
    "o1-mini":          (0.003,  0.012),
    "o1-preview":       (0.015,  0.060),
}

# Models that don't support system messages
_NO_SYSTEM_MODELS = {"o1-mini", "o1-preview", "o1"}


class OpenAIClient(BaseLLMClient):
    provider = "openai"

    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        self.model = model
        self._client = AsyncOpenAI(api_key=api_key)
        costs = _MODEL_COSTS.get(model, (0.001, 0.002))
        self._cost_per_1k_input = costs[0]
        self._cost_per_1k_output = costs[1]

    async def _call(
        self,
        system: str,
        user: str,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        try:
            messages = _build_messages(self.model, system, user)

            # Reasoning models (o1-*) don't support temperature
            kwargs: dict = {"model": self.model, "messages": messages, "max_tokens": max_tokens}
            if self.model not in _NO_SYSTEM_MODELS:
                kwargs["temperature"] = temperature

            completion = await self._client.chat.completions.create(**kwargs)

            content = completion.choices[0].message.content or ""
            usage = completion.usage

            input_tokens = usage.prompt_tokens if usage else 0
            output_tokens = usage.completion_tokens if usage else 0

            return LLMResponse(
                content=content,
                model=self.model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=self._compute_cost(input_tokens, output_tokens),
                raw=completion.model_dump() if hasattr(completion, "model_dump") else None,
            )

        except OAIRateLimit as exc:
            # Parse retry-after from headers if available
            retry_after = _parse_retry_after(exc)
            raise RateLimitError("openai", retry_after_s=retry_after) from exc

        except APITimeoutError as exc:
            raise LLMTimeoutError("openai") from exc

        except APIStatusError as exc:
            raise LLMError(
                "openai",
                message=f"OpenAI API error {exc.status_code}: {exc.message}",
            ) from exc

        except Exception as exc:
            raise LLMError("openai", message=str(exc)) from exc


def _build_messages(model: str, system: str, user: str) -> list[dict]:
    if model in _NO_SYSTEM_MODELS:
        # o1 models: prepend system content into user message
        return [{"role": "user", "content": f"{system}\n\n{user}"}]
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def _parse_retry_after(exc: OAIRateLimit) -> Optional[int]:
    try:
        headers = exc.response.headers
        val = headers.get("retry-after") or headers.get("x-ratelimit-reset-requests")
        if val:
            return int(float(val))
    except Exception:
        pass
    return None
