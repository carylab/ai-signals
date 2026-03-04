"""
Tests for importance_score.
All pure-function tests — no DB, no network.
"""
from __future__ import annotations

import pytest

from app.services.scoring.importance import (
    compute_importance,
    _title_signal,
    _tag_signal,
    _depth_signal,
    _entity_signal,
)


class TestImportanceScore:
    """Tests for the composite importance scorer."""

    def test_tier1_source_high_score(self) -> None:
        score = compute_importance(
            source_priority=1,
            title="OpenAI launches GPT-5",
            tags=["LLM", "Product Launch"],
            companies=["OpenAI"],
            word_count=800,
        )
        assert score > 0.75, f"Expected >0.75, got {score}"

    def test_low_priority_source_lower_score(self) -> None:
        high = compute_importance(
            source_priority=1,
            title="AI update",
            tags=[],
            companies=[],
            word_count=200,
        )
        low = compute_importance(
            source_priority=9,
            title="AI update",
            tags=[],
            companies=[],
            word_count=200,
        )
        assert high > low

    def test_funding_news_boosted(self) -> None:
        with_funding = compute_importance(
            source_priority=3,
            title="Anthropic raises $2 billion in new round",
            tags=["Funding"],
            companies=["Anthropic"],
            word_count=600,
        )
        without_funding = compute_importance(
            source_priority=3,
            title="Anthropic shares research update",
            tags=[],
            companies=["Anthropic"],
            word_count=600,
        )
        assert with_funding > without_funding

    def test_tier1_company_boosts_score(self) -> None:
        with_tier1 = compute_importance(
            source_priority=3,
            title="New AI release",
            tags=[],
            companies=["OpenAI"],
            word_count=300,
        )
        no_tier1 = compute_importance(
            source_priority=3,
            title="New AI release",
            tags=[],
            companies=["RandomStartup"],
            word_count=300,
        )
        assert with_tier1 > no_tier1

    def test_long_article_scores_higher(self) -> None:
        long_form = compute_importance(
            source_priority=3, title="AI analysis",
            tags=[], companies=[], word_count=1500,
        )
        snippet = compute_importance(
            source_priority=3, title="AI analysis",
            tags=[], companies=[], word_count=50,
        )
        assert long_form > snippet

    def test_output_bounded_zero_to_one(self) -> None:
        for priority in range(1, 11):
            score = compute_importance(
                source_priority=priority,
                title="some title with launches and billion",
                tags=["Funding", "LLM", "Research", "Policy"],
                companies=["OpenAI", "Anthropic"],
                word_count=2000,
            )
            assert 0.0 <= score <= 1.0, f"Score out of bounds: {score}"

    def test_empty_article_still_returns_float(self) -> None:
        score = compute_importance(
            source_priority=5, title="", tags=[], companies=[], word_count=0
        )
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0


class TestTitleSignal:
    def test_acquisition_keyword(self) -> None:
        assert _title_signal("Google acquires DeepMind startup") > 0

    def test_no_keywords(self) -> None:
        assert _title_signal("Random words here") == 0.0

    def test_multiple_keywords_capped(self) -> None:
        title = "OpenAI launches billion-dollar acquisition breakthrough funding"
        score = _title_signal(title)
        assert score <= 0.30

    def test_case_insensitive(self) -> None:
        lower = _title_signal("company raises funds")
        upper = _title_signal("Company RAISES Funds")
        assert lower == upper


class TestTagSignal:
    def test_high_value_tags_boost(self) -> None:
        assert _tag_signal(["Funding"]) > 0
        assert _tag_signal(["Research"]) > 0

    def test_unknown_tag_no_boost(self) -> None:
        assert _tag_signal(["UnknownTag"]) == 0.0

    def test_multiple_tags_accumulate_capped(self) -> None:
        score = _tag_signal(["Funding", "Research", "Policy", "LLM", "Safety"])
        assert score <= 0.25

    def test_empty_tags(self) -> None:
        assert _tag_signal([]) == 0.0


class TestDepthSignal:
    def test_long_form(self) -> None:
        assert _depth_signal(1500) == 0.12

    def test_article(self) -> None:
        assert _depth_signal(700) == 0.08

    def test_summary(self) -> None:
        assert _depth_signal(250) == 0.04

    def test_snippet(self) -> None:
        assert _depth_signal(50) == 0.0


class TestEntitySignal:
    def test_tier1_company(self) -> None:
        assert _entity_signal(["OpenAI"]) == 0.12

    def test_case_insensitive(self) -> None:
        assert _entity_signal(["ANTHROPIC"]) == 0.12

    def test_unknown_company(self) -> None:
        assert _entity_signal(["SmallStartupXYZ"]) == 0.0

    def test_empty_list(self) -> None:
        assert _entity_signal([]) == 0.0
