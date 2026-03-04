"""
Unit tests for trend calculator.
Pure logic — no DB, no network.
"""
from __future__ import annotations

import pytest

from app.services.trend.calculator import (
    EntityCounts,
    EntityType,
    TrendResult,
    _sigmoid,
    _velocity,
    compute_trend_scores,
)


class TestVelocity:
    def test_growing_entity(self) -> None:
        # 10 articles this week vs 5 last week → +100%
        assert _velocity(10, 5) == pytest.approx(1.0)

    def test_shrinking_entity(self) -> None:
        # 5 articles vs 10 → -50%
        assert _velocity(5, 10) == pytest.approx(-0.5)

    def test_new_entity_no_prev(self) -> None:
        # No prior week → velocity derived from count alone
        v = _velocity(8, 0)
        assert v > 0.0
        assert v <= 4.0      # capped at +400%

    def test_disappeared_and_returned(self) -> None:
        # Zero articles this week
        assert _velocity(0, 5) == pytest.approx(-1.0)

    def test_stable_entity(self) -> None:
        assert _velocity(10, 10) == pytest.approx(0.0)

    def test_capped_at_max(self) -> None:
        # 100 articles vs 1 last week → capped at 4.0
        assert _velocity(100, 1) == pytest.approx(4.0)


class TestSigmoid:
    def test_zero_input(self) -> None:
        assert _sigmoid(0.0) == pytest.approx(0.5)

    def test_large_positive(self) -> None:
        assert _sigmoid(100.0) > 0.99

    def test_large_negative(self) -> None:
        assert _sigmoid(-100.0) < 0.01

    def test_output_range(self) -> None:
        for x in [-10, -1, 0, 1, 10]:
            result = _sigmoid(float(x))
            assert 0.0 < result < 1.0


class TestComputeTrendScores:
    def _make_entity(
        self,
        slug: str,
        count_7d: int,
        count_prev_7d: int,
        avg_importance: float = 0.5,
        name: str = "",
    ) -> EntityCounts:
        return EntityCounts(
            slug=slug,
            name=name or slug,
            entity_type=EntityType.TAG,
            count_7d=count_7d,
            count_prev_7d=count_prev_7d,
            count_1d=max(1, count_7d // 7),
            count_30d=count_7d * 4,
            avg_importance=avg_importance,
        )

    def test_returns_sorted_by_score(self) -> None:
        entities = [
            self._make_entity("low",  count_7d=1,  count_prev_7d=2),
            self._make_entity("high", count_7d=20, count_prev_7d=5),
            self._make_entity("mid",  count_7d=8,  count_prev_7d=8),
        ]
        results = compute_trend_scores(entities, max_count_7d=20)
        scores = [r.trend_score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_all_scores_in_range(self) -> None:
        entities = [
            self._make_entity(f"e{i}", count_7d=i, count_prev_7d=max(0, i - 2))
            for i in range(10)
        ]
        results = compute_trend_scores(entities, max_count_7d=9)
        for r in results:
            assert 0.0 <= r.trend_score <= 1.0

    def test_empty_input_returns_empty(self) -> None:
        assert compute_trend_scores([]) == []

    def test_high_velocity_boosts_score(self) -> None:
        fast = self._make_entity("fast", count_7d=10, count_prev_7d=1)
        slow = self._make_entity("slow", count_7d=10, count_prev_7d=10)

        fast_result = compute_trend_scores([fast], max_count_7d=10)[0]
        slow_result = compute_trend_scores([slow], max_count_7d=10)[0]

        assert fast_result.trend_score > slow_result.trend_score

    def test_importance_contributes_to_score(self) -> None:
        important = self._make_entity(
            "important", count_7d=5, count_prev_7d=5, avg_importance=0.9
        )
        unimportant = self._make_entity(
            "unimportant", count_7d=5, count_prev_7d=5, avg_importance=0.1
        )
        imp_result = compute_trend_scores([important], max_count_7d=5)[0]
        unimp_result = compute_trend_scores([unimportant], max_count_7d=5)[0]

        assert imp_result.trend_score > unimp_result.trend_score

    def test_velocity_stored_in_result(self) -> None:
        entity = self._make_entity("e", count_7d=10, count_prev_7d=5)
        result = compute_trend_scores([entity], max_count_7d=10)[0]
        assert result.velocity == pytest.approx(1.0)

    def test_single_entity_gets_max_count_score(self) -> None:
        """A single entity with count_7d == max_count_7d should score near 1."""
        entity = self._make_entity(
            "top", count_7d=100, count_prev_7d=50, avg_importance=1.0
        )
        result = compute_trend_scores([entity], max_count_7d=100)[0]
        assert result.trend_score > 0.85

    def test_zero_count_entity_scores_low(self) -> None:
        entity = self._make_entity("cold", count_7d=0, count_prev_7d=0)
        result = compute_trend_scores([entity], max_count_7d=100)[0]
        assert result.trend_score < 0.3


class TestEntityCounts:
    def test_dataclass_defaults(self) -> None:
        ec = EntityCounts(slug="test", name="Test", entity_type=EntityType.TAG)
        assert ec.count_1d == 0
        assert ec.count_7d == 0
        assert ec.avg_importance == 0.0
