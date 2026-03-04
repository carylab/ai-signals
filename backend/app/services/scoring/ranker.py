"""
Ranker — combines sub-scores into final_score and provides
batch ranking utilities.

final_score = (
    importance  × W_IMPORTANCE  +
    freshness   × W_FRESHNESS   +
    trend       × W_TREND       +
    discussion  × W_DISCUSSION
)

Weights reflect editorial priorities:
  importance  0.40 — What it is matters most
  freshness   0.30 — Recency is critical for a news platform
  trend       0.20 — Riding current conversations amplifies reach
  discussion  0.10 — Coverage breadth is a weak but real signal

All weights sum to 1.0.  The final score is NOT sigmoid-transformed
because each sub-score is already in [0,1] and a linear combination
of bounded inputs is already bounded.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


# ---------------------------------------------------------------------------
# Weights — must sum to 1.0
# ---------------------------------------------------------------------------

W_IMPORTANCE  = 0.40
W_FRESHNESS   = 0.30
W_TREND       = 0.20
W_DISCUSSION  = 0.10

assert abs(W_IMPORTANCE + W_FRESHNESS + W_TREND + W_DISCUSSION - 1.0) < 1e-9


@dataclass
class ArticleScores:
    """All score dimensions for a single article."""
    importance:  float
    freshness:   float
    trend:       float
    discussion:  float

    @property
    def final(self) -> float:
        return round(
            self.importance  * W_IMPORTANCE
            + self.freshness * W_FRESHNESS
            + self.trend     * W_TREND
            + self.discussion * W_DISCUSSION,
            6,
        )

    def to_dict(self) -> dict[str, float]:
        return {
            "importance_score":  round(self.importance, 4),
            "freshness_score":   round(self.freshness,  4),
            "trend_score":       round(self.trend,       4),
            "discussion_score":  round(self.discussion,  4),
            "final_score":       round(self.final,       4),
        }


def compute_final_score(
    importance: float,
    freshness: float,
    trend: float,
    discussion: float,
) -> float:
    """
    Compute weighted final score.
    Clamps each input to [0, 1] defensively.
    """
    return ArticleScores(
        importance=_clamp(importance),
        freshness=_clamp(freshness),
        trend=_clamp(trend),
        discussion=_clamp(discussion),
    ).final


def rank_articles(
    articles: Sequence[dict],
    *,
    min_score: float = 0.0,
    max_results: int = 0,
    reps_only: bool = False,
) -> list[dict]:
    """
    Sort articles by final_score descending.

    Args:
        articles:    list of article dicts (must contain "final_score")
        min_score:   exclude articles below this threshold
        max_results: cap result count (0 = no cap)
        reps_only:   if True, only include cluster representatives

    Returns:
        filtered and sorted list
    """
    filtered = [
        a for a in articles
        if a.get("final_score", 0.0) >= min_score
        and (not reps_only or a.get("is_cluster_representative", True))
    ]
    filtered.sort(key=lambda a: a.get("final_score", 0.0), reverse=True)

    if max_results > 0:
        return filtered[:max_results]
    return filtered


def score_percentile(score: float, all_scores: list[float]) -> float:
    """
    Return the percentile rank of `score` within `all_scores`.
    Useful for relative ranking display ("Top 5%").
    """
    if not all_scores:
        return 0.0
    below = sum(1 for s in all_scores if s < score)
    return round(below / len(all_scores) * 100, 1)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))
