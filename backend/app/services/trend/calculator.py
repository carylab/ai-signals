"""
Trend score calculator.

For each entity (tag / company / ai_model), computes:

  trend_score = sigmoid(
      w_count    * normalised_count_7d    +
      w_velocity * velocity               +
      w_importance * avg_importance_score
  )

  velocity = (count_7d - count_prev_7d) / max(count_prev_7d, 1)
           → positive means growing, negative means shrinking

The sigmoid maps an arbitrary linear combination to (0, 1) without
hard clamping — entities at the extremes still have meaningful scores.

All calculations are pure Python (no ML dependencies for MVP).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence


@dataclass
class EntityCounts:
    """Raw article counts for a single entity over different windows."""
    slug: str
    name: str
    entity_type: str            # "tag" | "company" | "ai_model"

    count_1d: int = 0
    count_7d: int = 0
    count_30d: int = 0
    count_prev_7d: int = 0      # days 8–14 ago (for velocity)
    avg_importance: float = 0.0


@dataclass
class TrendResult:
    """Computed trend metrics for a single entity."""
    slug: str
    name: str
    entity_type: str

    count_1d: int
    count_7d: int
    count_30d: int
    count_prev_7d: int
    avg_importance: float

    velocity: float             # (count_7d - count_prev_7d) / prev
    trend_score: float          # 0.0 – 1.0


# Score weights
_W_COUNT = 0.50
_W_VELOCITY = 0.30
_W_IMPORTANCE = 0.20

# Normalisation denominator for count signal
# Articles that exceed this in 7d are considered "saturated"
_COUNT_SATURATION = 30.0


def compute_trend_scores(
    entities: Sequence[EntityCounts],
    max_count_7d: int = 0,
) -> list[TrendResult]:
    """
    Compute trend scores for a batch of entities.

    Args:
        entities:     list of EntityCounts
        max_count_7d: the maximum count_7d in the batch (used for
                      relative normalisation when >0)

    Returns:
        list of TrendResult sorted by trend_score descending
    """
    if not entities:
        return []

    # Use relative normalisation if we have a meaningful max
    normaliser = float(max(max_count_7d, 1))

    results: list[TrendResult] = []
    for ec in entities:
        velocity = _velocity(ec.count_7d, ec.count_prev_7d)
        score = _trend_score(
            count_7d=ec.count_7d,
            velocity=velocity,
            avg_importance=ec.avg_importance,
            normaliser=normaliser,
        )
        results.append(TrendResult(
            slug=ec.slug,
            name=ec.name,
            entity_type=ec.entity_type,
            count_1d=ec.count_1d,
            count_7d=ec.count_7d,
            count_30d=ec.count_30d,
            count_prev_7d=ec.count_prev_7d,
            avg_importance=ec.avg_importance,
            velocity=round(velocity, 4),
            trend_score=round(score, 4),
        ))

    results.sort(key=lambda r: r.trend_score, reverse=True)
    return results


# ---------------------------------------------------------------------------
# Internal calculations
# ---------------------------------------------------------------------------

def _velocity(count_7d: int, count_prev_7d: int) -> float:
    """
    Velocity = relative growth rate.

    Examples:
        10 articles this week vs 5 last week → velocity = 1.0  (+100%)
        5 articles this week vs 10 last week → velocity = -0.5 (-50%)
        5 articles this week vs 0 last week  → velocity = 4.0  (capped)
    """
    if count_prev_7d == 0:
        # New entity or entity that disappeared for a week then re-appeared
        return min(float(count_7d) / 2.0, 4.0)  # cap at +400%

    raw = (count_7d - count_prev_7d) / float(count_prev_7d)
    return max(-1.0, min(raw, 4.0))  # clamp to [-100%, +400%]


def _trend_score(
    count_7d: int,
    velocity: float,
    avg_importance: float,
    normaliser: float,
) -> float:
    """
    Combine signals into a single trend score in (0, 1) via sigmoid.

    count signal:    log-normalised count relative to batch maximum
    velocity signal: mapped from [-1, +4] to [0, 1]
    importance:      already in [0, 1]
    """
    # Count signal: log scale prevents one mega-topic dominating
    count_signal = math.log1p(count_7d) / math.log1p(max(normaliser, 1))

    # Velocity signal: map [-1, +4] → [0, 1]
    # -1.0 → 0.0,  0.0 → 0.2,  1.0 → 0.4,  4.0 → 1.0
    velocity_signal = (velocity + 1.0) / 5.0
    velocity_signal = max(0.0, min(velocity_signal, 1.0))

    linear = (
        _W_COUNT * count_signal
        + _W_VELOCITY * velocity_signal
        + _W_IMPORTANCE * avg_importance
    )

    return _sigmoid(linear * 6 - 3)   # stretch input so sigmoid uses its full range


def _sigmoid(x: float) -> float:
    """Standard logistic function. Clipped to avoid overflow."""
    x = max(-500.0, min(500.0, x))
    return 1.0 / (1.0 + math.exp(-x))
