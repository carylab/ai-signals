"""
OpenRouter provider client.

OpenRouter aggregates 100+ models under a single OpenAI-compatible API.
Useful for:
  - Cost comparison across providers
  - Fallback when primary provider is down
  - Accessing models not available directly (Gemini, Cohere, etc.)

Model IDs follow the pattern:  "provider/model-name"
Examples:
  - openai/gpt-4o-mini
  - anthropic/claude-3-5-haiku
  - google/gemini-flash-1.5
  - meta-llama/llama-3.1-70b-instruct
  - mistralai/mistral-nemo

Set LLM_MODEL to the full OpenRouter model ID when using this provider.
"""
from __future__ import annotations

import structlog
from openai import AsyncOpenAI, APIStatusError, APITimeoutError
from openai import RateLimitError as OAIRateLimit

from app.services.llm.base import BaseLLMClient, LLMResponse
from app.core.exceptions import LLMError, LLMTimeoutError, RateLimitError
from app.config import settings

logger = structlog.get_logger(__name__)

_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


class OpenRouterClient(BaseLLMClient):
    provider = "openrouter"

    def __init__(self, api_key: str, model: str = "openai/gpt-4o-mini") -> None:
        self.model = model
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=_OPENROUTER_BASE_URL,
            default_headers={
                # OpenRouter requires these for usage tracking / leaderboard
                "HTTP-Referer": "https://aisignals.io",
                "X-Title": settings.app_name,
            },
        )
        # OpenRouter returns cost in the response; we'll use that when available
        self._cost_per_1k_input = 0.0
        self._cost_per_1k_output = 0.0

    async def _call(
        self,
        system: str,
        user: str,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        try:
            completion = await self._client.chat.completions.create(
                model=self.model,
                temperature=temperature,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )

            content = completion.choices[0].message.content or ""
            usage = completion.usage
            input_tokens = usage.prompt_tokens if usage else 0
            output_tokens = usage.completion_tokens if usage else 0

            # OpenRouter may return actual cost in usage extensions
            cost = 0.0
            if usage and hasattr(usage, "cost"):
                cost = float(usage.cost or 0)  # type: ignore[attr-defined]
            else:
                cost = self._compute_cost(input_tokens, output_tokens)

            return LLMResponse(
                content=content,
                model=self.model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost,
            )

        except OAIRateLimit as exc:
            raise RateLimitError("openrouter") from exc

        except APITimeoutError as exc:
            raise LLMTimeoutError("openrouter") from exc

        except APIStatusError as exc:
            raise LLMError(
                "openrouter",
                message=f"OpenRouter API error {exc.status_code}: {exc.message}",
            ) from exc

        except Exception as exc:
            raise LLMError("openrouter", message=str(exc)) from exc
