"""
DeepSeek provider client.

DeepSeek exposes an OpenAI-compatible API, so we reuse the openai
SDK with a custom base_url — no additional dependency required.

Supported models:
  - deepseek-chat     (DeepSeek-V3, best value)
  - deepseek-reasoner (DeepSeek-R1, reasoning)
"""
from __future__ import annotations

import structlog
from openai import AsyncOpenAI, APIStatusError, APITimeoutError
from openai import RateLimitError as OAIRateLimit

from app.services.llm.base import BaseLLMClient, LLMResponse
from app.core.exceptions import LLMError, LLMTimeoutError, RateLimitError

logger = structlog.get_logger(__name__)

_DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"

_MODEL_COSTS: dict[str, tuple[float, float]] = {
    # prices as of early 2026 (cache miss / cache hit differ; using miss)
    "deepseek-chat":     (0.00027, 0.0011),
    "deepseek-reasoner": (0.00055, 0.00219),
}


class DeepSeekClient(BaseLLMClient):
    provider = "deepseek"

    def __init__(self, api_key: str, model: str = "deepseek-chat") -> None:
        self.model = model
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=_DEEPSEEK_BASE_URL,
        )
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

            return LLMResponse(
                content=content,
                model=self.model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=self._compute_cost(input_tokens, output_tokens),
            )

        except OAIRateLimit as exc:
            raise RateLimitError("deepseek") from exc

        except APITimeoutError as exc:
            raise LLMTimeoutError("deepseek") from exc

        except APIStatusError as exc:
            raise LLMError(
                "deepseek",
                message=f"DeepSeek API error {exc.status_code}: {exc.message}",
            ) from exc

        except Exception as exc:
            raise LLMError("deepseek", message=str(exc)) from exc
