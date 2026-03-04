"""
Tests for freshness_score, trend_score, discussion_score, and ranker.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.services.scoring.freshness import compute_freshness, freshness_at_age
from app.services.scoring.trend_score import compute_trend
from app.services.scoring.discussion import compute_discussion
from app.services.scoring.ranker import (
    ArticleScores,
    compute_final_score,
    rank_articles,
    score_percentile,
    W_IMPORTANCE, W_FRESHNESS, W_TREND, W_DISCUSSION,
)


# ─────────────────────────────────────────────────────────────────────────────
# Freshness
# ─────────────────────────────────────────────────────────────────────────────

class TestFreshnessScore:
    _NOW = datetime(2026, 3, 4, 12, 0, 0, tzinfo=timezone.utc)

    def _pub(self, hours_ago: float) -> datetime:
        return self._NOW - timedelta(hours=hours_ago)

    def test_brand_new_article(self) -> None:
        score = compute_freshness(self._pub(0), now=self._NOW)
        assert score == pytest.approx(1.0, abs=0.01)

    def test_half_life_24h(self) -> None:
        score = compute_freshness(self._pub(24), now=self._NOW)
        assert score == pytest.approx(0.5, abs=0.01)

    def test_48h_quarter_score(self) -> None:
        score = compute_freshness(self._pub(48), now=self._NOW)
        assert score == pytest.approx(0.25, abs=0.01)

    def test_beyond_max_age_zero(self) -> None:
        score = compute_freshness(self._pub(200), now=self._NOW)
        assert score == 0.0

    def test_future_article_treated_as_now(self) -> None:
        future = self._NOW + timedelta(hours=2)
        score = compute_freshness(future, now=self._NOW)
        assert score == pytest.approx(1.0, abs=0.01)

    def test_none_published_at_returns_default(self) -> None:
        score = compute_freshness(None)
        assert 0.0 < score < 1.0

    def test_iso_string_input(self) -> None:
        pub_str = (self._NOW - timedelta(hours=12)).isoformat()
        score = compute_freshness(pub_str, now=self._NOW)
        assert score == pytest.approx(0.707, abs=0.01)

    def test_monotonically_decreasing(self) -> None:
        scores = [compute_freshness(self._pub(h), now=self._NOW)
                  for h in [0, 6, 12, 24, 48, 72]]
        assert scores == sorted(scores, reverse=True)

    def test_freshness_at_age_utility(self) -> None:
        assert freshness_at_age(0)  == pytest.approx(1.0)
        assert freshness_at_age(24) == pytest.approx(0.5, abs=0.01)


# ─────────────────────────────────────────────────────────────────────────────
# Trend Score
# ─────────────────────────────────────────────────────────────────────────────

class TestTrendScore:
    _TAG_TRENDS = {
        "llm":         0.90,
        "funding":     0.75,
        "open-source": 0.60,
        "policy":      0.40,
    }
    _COMPANY_TRENDS = {
        "openai":    0.95,
        "anthropic": 0.80,
    }
    _MODEL_TRENDS = {
        "gpt-4o": 0.70,
    }

    def test_trending_tag_propagates(self) -> None:
        score = compute_trend(
            tags=["LLM"],
            companies=[],
            ai_models=[],
            tag_trend_scores=self._TAG_TRENDS,
            company_trend_scores={},
            model_trend_scores={},
        )
        assert score == pytest.approx(0.90, abs=0.001)

    def test_company_trend_weighted_down(self) -> None:
        tag_score = compute_trend(
            tags=["LLM"],
            companies=[],
            ai_models=[],
            tag_trend_scores={"llm": 0.90},
            company_trend_scores={},
            model_trend_scores={},
        )
        company_score = compute_trend(
            tags=[],
            companies=["OpenAI"],
            ai_models=[],
            tag_trend_scores={},
            company_trend_scores={"openai": 0.90},
            model_trend_scores={},
        )
        # Company score should be 0.90 × 0.85 = 0.765
        assert company_score < tag_score
        assert company_score == pytest.approx(0.90 * 0.85, abs=0.001)

    def test_multiple_tags_takes_max(self) -> None:
        score = compute_trend(
            tags=["LLM", "Policy"],
            companies=[],
            ai_models=[],
            tag_trend_scores=self._TAG_TRENDS,
            company_trend_scores={},
            model_trend_scores={},
        )
        assert score == pytest.approx(0.90, abs=0.001)  # max of 0.90 and 0.40

    def test_unknown_tags_score_zero(self) -> None:
        score = compute_trend(
            tags=["UnknownTag"],
            companies=[],
            ai_models=[],
            tag_trend_scores=self._TAG_TRENDS,
            company_trend_scores={},
            model_trend_scores={},
        )
        assert score == 0.0

    def test_empty_article_score_zero(self) -> None:
        score = compute_trend([], [], [], {}, {}, {})
        assert score == 0.0

    def test_output_bounded(self) -> None:
        score = compute_trend(
            tags=["LLM", "Funding"],
            companies=["OpenAI"],
            ai_models=["GPT-4o"],
            tag_trend_scores=self._TAG_TRENDS,
            company_trend_scores=self._COMPANY_TRENDS,
            model_trend_scores=self._MODEL_TRENDS,
        )
        assert 0.0 <= score <= 1.0


# ─────────────────────────────────────────────────────────────────────────────
# Discussion Score
# ─────────────────────────────────────────────────────────────────────────────

class TestDiscussionScore:
    def test_solo_article_zero(self) -> None:
        assert compute_discussion(cluster_size=1) == 0.0

    def test_two_sources_positive(self) -> None:
        score = compute_discussion(cluster_size=2)
        assert score > 0.0

    def test_saturated_cluster_approaches_one(self) -> None:
        score = compute_discussion(cluster_size=20)
        assert score >= 0.99

    def test_community_source_boost(self) -> None:
        base = compute_discussion(cluster_size=1, source_category="media")
        community = compute_discussion(cluster_size=1, source_category="community")
        assert community > base

    def test_score_monotonically_increasing(self) -> None:
        scores = [compute_discussion(i) for i in range(1, 15)]
        assert scores == sorted(scores)

    def test_output_bounded(self) -> None:
        for size in [1, 5, 10, 20, 50, 100]:
            score = compute_discussion(size)
            assert 0.0 <= score <= 1.0


# ─────────────────────────────────────────────────────────────────────────────
# Ranker
# ─────────────────────────────────────────────────────────────────────────────

class TestArticleScores:
    def test_final_score_weighted_sum(self) -> None:
        scores = ArticleScores(
            importance=0.8,
            freshness=0.6,
            trend=0.4,
            discussion=0.2,
        )
        expected = (
            0.8 * W_IMPORTANCE
            + 0.6 * W_FRESHNESS
            + 0.4 * W_TREND
            + 0.2 * W_DISCUSSION
        )
        assert scores.final == pytest.approx(expected, abs=1e-6)

    def test_to_dict_has_all_keys(self) -> None:
        scores = ArticleScores(0.5, 0.5, 0.5, 0.5)
        d = scores.to_dict()
        assert "importance_score" in d
        assert "freshness_score" in d
        assert "trend_score" in d
        assert "discussion_score" in d
        assert "final_score" in d

    def test_weights_sum_to_one(self) -> None:
        total = W_IMPORTANCE + W_FRESHNESS + W_TREND + W_DISCUSSION
        assert total == pytest.approx(1.0, abs=1e-9)


class TestComputeFinalScore:
    def test_all_ones_returns_one(self) -> None:
        assert compute_final_score(1.0, 1.0, 1.0, 1.0) == pytest.approx(1.0)

    def test_all_zeros_returns_zero(self) -> None:
        assert compute_final_score(0.0, 0.0, 0.0, 0.0) == pytest.approx(0.0)

    def test_over_one_clamped(self) -> None:
        score = compute_final_score(1.5, 1.5, 1.5, 1.5)
        assert score == pytest.approx(1.0)

    def test_below_zero_clamped(self) -> None:
        score = compute_final_score(-0.5, -0.5, -0.5, -0.5)
        assert score == pytest.approx(0.0)

    def test_importance_weighted_most(self) -> None:
        imp_dominant = compute_final_score(1.0, 0.0, 0.0, 0.0)
        fresh_dominant = compute_final_score(0.0, 1.0, 0.0, 0.0)
        assert imp_dominant > fresh_dominant  # 0.40 > 0.30


class TestRankArticles:
    def _make(self, slug: str, score: float, rep: bool = True) -> dict:
        return {
            "slug": slug,
            "final_score": score,
            "is_cluster_representative": rep,
        }

    def test_sorted_descending(self) -> None:
        articles = [
            self._make("c", 0.3),
            self._make("a", 0.9),
            self._make("b", 0.6),
        ]
        result = rank_articles(articles)
        assert [a["slug"] for a in result] == ["a", "b", "c"]

    def test_min_score_filter(self) -> None:
        articles = [self._make("a", 0.8), self._make("b", 0.1)]
        result = rank_articles(articles, min_score=0.5)
        assert len(result) == 1
        assert result[0]["slug"] == "a"

    def test_max_results_cap(self) -> None:
        articles = [self._make(str(i), float(i) / 10) for i in range(10)]
        result = rank_articles(articles, max_results=3)
        assert len(result) == 3

    def test_reps_only_filter(self) -> None:
        articles = [
            self._make("rep", 0.9, rep=True),
            self._make("nonrep", 0.8, rep=False),
        ]
        result = rank_articles(articles, reps_only=True)
        assert len(result) == 1
        assert result[0]["slug"] == "rep"

    def test_empty_input(self) -> None:
        assert rank_articles([]) == []


class TestScorePercentile:
    def test_top_score(self) -> None:
        scores = [0.1, 0.3, 0.5, 0.7, 0.9]
        assert score_percentile(0.9, scores) == 80.0  # 4 below

    def test_bottom_score(self) -> None:
        scores = [0.1, 0.3, 0.5]
        assert score_percentile(0.1, scores) == 0.0

    def test_empty_scores(self) -> None:
        assert score_percentile(0.5, []) == 0.0
