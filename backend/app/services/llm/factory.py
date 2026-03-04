"""
LLM client factory.

create_llm_client() reads LLM_PROVIDER and the corresponding API key
from settings and returns the appropriate BaseLLMClient subclass.

The returned client is stateless (no session, no connection pool at
the client level) so it is safe to call create_llm_client() multiple
times — each call returns a fresh instance backed by the same
underlying HTTP connection pool managed by the SDK.

For dependency injection into FastAPI routes, use the Depends() wrapper
defined in app.dependencies.
"""
from __future__ import annotations

from functools import lru_cache

import structlog

from app.config import settings
from app.services.llm.base import BaseLLMClient

logger = structlog.get_logger(__name__)


def create_llm_client(
    provider: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
) -> BaseLLMClient:
    """
    Create and return an LLM client for the configured provider.

    Args:
        provider: Override settings.llm_provider (useful in tests)
        model:    Override settings.llm_model
        api_key:  Override the provider API key (useful in tests)

    Raises:
        ValueError: if the provider is unknown or API key is missing
    """
    _provider = provider or settings.llm_provider
    _model = model or settings.llm_model
    _key = api_key or settings.active_llm_key

    if not _key and settings.app_env != "test":
        raise ValueError(
            f"No API key found for provider {_provider!r}. "
            "Set the corresponding environment variable."
        )

    logger.debug(
        "llm_client_created",
        provider=_provider,
        model=_model,
    )

    if _provider == "openai":
        from app.services.llm.openai_client import OpenAIClient
        return OpenAIClient(api_key=_key or "", model=_model)

    if _provider == "anthropic":
        from app.services.llm.anthropic_client import AnthropicClient
        return AnthropicClient(api_key=_key or "", model=_model)

    if _provider == "deepseek":
        from app.services.llm.deepseek_client import DeepSeekClient
        return DeepSeekClient(api_key=_key or "", model=_model)

    if _provider == "openrouter":
        from app.services.llm.openrouter_client import OpenRouterClient
        return OpenRouterClient(api_key=_key or "", model=_model)

    raise ValueError(
        f"Unknown LLM provider: {_provider!r}. "
        "Valid options: openai, anthropic, deepseek, openrouter"
    )


class MockLLMClient(BaseLLMClient):
    """
    In-memory mock client for unit tests.
    Returns configurable canned responses without making network calls.

    Usage:
        mock = MockLLMClient(json_response={"summary": "test", "bullets": []})
        result = await mock.complete_json(system="...", user="...")
    """

    provider = "mock"
    model = "mock-model"

    def __init__(
        self,
        text_response: str = "Mock response.",
        json_response: dict | None = None,
        raise_error: Exception | None = None,
    ) -> None:
        self._text = text_response
        self._json = json_response or {}
        self._raise = raise_error
        self.call_count = 0
        self.last_system: str = ""
        self.last_user: str = ""

    async def _call(
        self,
        system: str,
        user: str,
        temperature: float,
        max_tokens: int,
    ) -> "LLMResponse":
        from app.services.llm.base import LLMResponse
        import json

        self.call_count += 1
        self.last_system = system
        self.last_user = user

        if self._raise:
            raise self._raise

        content = json.dumps(self._json) if self._json else self._text
        return LLMResponse(
            content=content,
            model=self.model,
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.0,
        )
