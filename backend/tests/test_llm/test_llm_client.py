"""
Unit tests for LLM base client and factory.
No real API calls — uses MockLLMClient.
"""
from __future__ import annotations

import json

import pytest

from app.services.llm.base import BaseLLMClient, LLMResponse, _try_parse_json
from app.services.llm.factory import MockLLMClient, create_llm_client


# ---------------------------------------------------------------------------
# _try_parse_json
# ---------------------------------------------------------------------------

class TestTryParseJson:
    def test_pure_json(self) -> None:
        result = _try_parse_json('{"key": "value"}')
        assert result == {"key": "value"}

    def test_fenced_json(self) -> None:
        text = '```json\n{"key": "value"}\n```'
        result = _try_parse_json(text)
        assert result == {"key": "value"}

    def test_json_with_prose(self) -> None:
        text = 'Here is the JSON:\n{"key": "value"}\nDone.'
        result = _try_parse_json(text)
        assert result == {"key": "value"}

    def test_invalid_json_returns_none(self) -> None:
        assert _try_parse_json("not json at all") is None

    def test_empty_string_returns_none(self) -> None:
        assert _try_parse_json("") is None

    def test_json_array_returns_none(self) -> None:
        # We expect a dict, not a list
        assert _try_parse_json("[1, 2, 3]") is None


# ---------------------------------------------------------------------------
# MockLLMClient
# ---------------------------------------------------------------------------

class TestMockLLMClient:
    @pytest.mark.asyncio
    async def test_complete_returns_text(self) -> None:
        mock = MockLLMClient(text_response="Hello world")
        response = await mock.complete(system="sys", user="user")
        assert response.content == "Hello world"
        assert response.model == "mock-model"
        assert mock.call_count == 1

    @pytest.mark.asyncio
    async def test_complete_json_returns_dict(self) -> None:
        payload = {"summary": "test summary", "bullets": ["a", "b", "c"]}
        mock = MockLLMClient(json_response=payload)
        result = await mock.complete_json(system="sys", user="user")
        assert result["summary"] == "test summary"
        assert result["bullets"] == ["a", "b", "c"]

    @pytest.mark.asyncio
    async def test_complete_json_retries_on_bad_json(self) -> None:
        """
        First call returns bad JSON, second returns valid JSON.
        The client should retry and succeed.
        """
        responses = iter(["not json", '{"summary": "fixed"}'])

        class SequentialMock(MockLLMClient):
            async def _call(self, system, user, temperature, max_tokens):
                content = next(responses)
                return LLMResponse(
                    content=content, model="mock", input_tokens=10, output_tokens=5
                )

        mock = SequentialMock()
        result = await mock.complete_json(
            system="sys", user="user", max_parse_retries=1
        )
        assert result["summary"] == "fixed"

    @pytest.mark.asyncio
    async def test_complete_json_raises_after_max_retries(self) -> None:
        from app.core.exceptions import LLMParseError

        mock = MockLLMClient(text_response="definitely not json")
        with pytest.raises(LLMParseError):
            await mock.complete_json(system="sys", user="user", max_parse_retries=1)

    @pytest.mark.asyncio
    async def test_tracks_call_context(self) -> None:
        mock = MockLLMClient(json_response={"ok": True})
        await mock.complete_json(system="my system", user="my user")
        assert mock.last_system.startswith("my system")
        assert "my user" in mock.last_user

    @pytest.mark.asyncio
    async def test_raises_configured_error(self) -> None:
        from app.core.exceptions import LLMError

        mock = MockLLMClient(raise_error=LLMError("mock", "forced failure"))
        with pytest.raises(LLMError, match="forced failure"):
            await mock.complete(system="s", user="u")


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

class TestFactory:
    def test_creates_openai_client(self, monkeypatch) -> None:
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

        from app.services.llm.openai_client import OpenAIClient
        client = create_llm_client(
            provider="openai", model="gpt-4o-mini", api_key="sk-test"
        )
        assert isinstance(client, OpenAIClient)
        assert client.model == "gpt-4o-mini"
        assert client.provider == "openai"

    def test_creates_anthropic_client(self) -> None:
        from app.services.llm.anthropic_client import AnthropicClient
        client = create_llm_client(
            provider="anthropic",
            model="claude-3-5-haiku-20241022",
            api_key="sk-ant-test",
        )
        assert isinstance(client, AnthropicClient)

    def test_creates_deepseek_client(self) -> None:
        from app.services.llm.deepseek_client import DeepSeekClient
        client = create_llm_client(
            provider="deepseek", model="deepseek-chat", api_key="sk-test"
        )
        assert isinstance(client, DeepSeekClient)

    def test_creates_openrouter_client(self) -> None:
        from app.services.llm.openrouter_client import OpenRouterClient
        client = create_llm_client(
            provider="openrouter",
            model="openai/gpt-4o-mini",
            api_key="sk-or-test",
        )
        assert isinstance(client, OpenRouterClient)

    def test_raises_on_unknown_provider(self) -> None:
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            create_llm_client(provider="unknown", api_key="key")


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

class TestPrompts:
    def test_summarize_prompt_contains_title(self) -> None:
        from app.services.llm.prompts.summarize import build_summarize_prompt

        prompt = build_summarize_prompt(
            title="OpenAI launches GPT-5",
            content="Full article text here...",
            source="techcrunch-ai",
        )
        assert "OpenAI launches GPT-5" in prompt
        assert "techcrunch-ai" in prompt
        assert "JSON" in prompt

    def test_tagging_prompt_contains_title(self) -> None:
        from app.services.llm.prompts.tagging import build_tagging_prompt

        prompt = build_tagging_prompt(
            title="Anthropic raises $2B",
            summary="Anthropic secures new funding round.",
        )
        assert "Anthropic raises $2B" in prompt

    def test_brief_prompt_formats_articles(self) -> None:
        from app.services.llm.prompts.brief import build_brief_prompt

        articles = [
            {"title": "Story A", "summary": "Summary A", "score": 0.9},
            {"title": "Story B", "summary": "Summary B", "score": 0.7},
        ]
        prompt = build_brief_prompt(
            date="2026-03-04",
            articles=articles,
            trending_tags=["LLM", "Funding"],
        )
        assert "2026-03-04" in prompt
        assert "Story A" in prompt
        assert "LLM" in prompt
