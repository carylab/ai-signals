"""
Anthropic provider client.

Supports Claude model family via the official anthropic SDK (v0.26+).
Uses the Messages API (not legacy Text Completions).

Supported models:
  - claude-3-5-haiku-20241022   (fast, cost-efficient)
  - claude-3-5-sonnet-20241022  (balanced)
  - claude-opus-4-5             (most capable)
"""
from __future__ import annotations

import structlog
import anthropic
from anthropic import AsyncAnthropic, APIStatusError, APITimeoutError

from app.services.llm.base import BaseLLMClient, LLMResponse
from app.core.exceptions import LLMError, LLMTimeoutError, RateLimitError

logger = structlog.get_logger(__name__)

_MODEL_COSTS: dict[str, tuple[float, float]] = {
    "claude-3-5-haiku-20241022":  (0.001,  0.005),
    "claude-3-5-sonnet-20241022": (0.003,  0.015),
    "claude-3-opus-20240229":     (0.015,  0.075),
    "claude-opus-4-5":            (0.015,  0.075),
}

_DEFAULT_MAX_TOKENS = 1024


class AnthropicClient(BaseLLMClient):
    provider = "anthropic"

    def __init__(self, api_key: str, model: str = "claude-3-5-haiku-20241022") -> None:
        self.model = model
        self._client = AsyncAnthropic(api_key=api_key)
        costs = _MODEL_COSTS.get(model, (0.003, 0.015))
        self._cost_per_1k_input = costs[0]
        self._cost_per_1k_output = costs[1]

    async def _call(
        self,
        system: str,
        user: str,
        temperature: float = 0.3,
        max_tokens: int = _DEFAULT_MAX_TOKENS,
    ) -> LLMResponse:
        try:
            message = await self._client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                messages=[{"role": "user", "content": user}],
            )

            # Extract text from content blocks
            content = ""
            for block in message.content:
                if hasattr(block, "text"):
                    content += block.text

            input_tokens = message.usage.input_tokens
            output_tokens = message.usage.output_tokens

            return LLMResponse(
                content=content,
                model=self.model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=self._compute_cost(input_tokens, output_tokens),
                raw={
                    "id": message.id,
                    "stop_reason": message.stop_reason,
                },
            )

        except anthropic.RateLimitError as exc:
            raise RateLimitError("anthropic") from exc

        except APITimeoutError as exc:
            raise LLMTimeoutError("anthropic") from exc

        except APIStatusError as exc:
            raise LLMError(
                "anthropic",
                message=f"Anthropic API error {exc.status_code}: {exc.message}",
            ) from exc

        except Exception as exc:
            raise LLMError("anthropic", message=str(exc)) from exc
