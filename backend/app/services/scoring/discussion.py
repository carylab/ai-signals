"""
Discussion Score  (0.0 – 1.0)

Proxy for social / editorial attention — how widely is this story
being covered?

Signals:
  cluster_size    — number of sources covering the same story
                    (primary signal, available for all articles)
  source_category — community sources (HN, Reddit) get a moderate boost
                    because high-upvote community posts are strong signals

Formula (cluster-based):
  base = log(cluster_size) / log(MAX_CLUSTER)
  community_boost = 0.10 if source_category in {"community"} else 0.0
  score = min(base + community_boost, 1.0)

Rationale for log scale:
  cluster_size=1  → 0.00  (nobody else covered it)
  cluster_size=2  → 0.30  (one other source)
  cluster_size=5  → 0.58
  cluster_size=10 → 0.77
  cluster_size=20 → 1.00  ← saturation point

V2 upgrade: add HN points / Reddit upvotes via dedicated fetchers.
"""
from __future__ import annotations

import math

_MAX_CLUSTER = 20.0      # cluster size that saturates the score
_COMMUNITY_BOOST = 0.10  # bonus for community-sourced articles


def compute_discussion(
    cluster_size: int,
    source_category: str = "",
) -> float:
    """
    Compute discussion_score for a single article.

    Args:
        cluster_size:     number of articles in this story cluster
                          (1 = no other sources covered it)
        source_category:  NewsSource.category (e.g. "community", "media")

    Returns:
        float in [0.0, 1.0]
    """
    size = max(1, cluster_size)

    if size == 1:
        base = 0.0
    else:
        base = math.log(size) / math.log(_MAX_CLUSTER)

    community_boost = _COMMUNITY_BOOST if source_category == "community" else 0.0

    return round(min(base + community_boost, 1.0), 6)
