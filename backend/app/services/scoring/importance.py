"""
Importance Score  (0.0 – 1.0)

Measures how significant an article is based on static signals
that do not change over time (unlike freshness/trend).

Signal stack:
  source_base      — publisher authority (from source.priority 1–10)
  title_signals    — high-value keywords in the title
  tag_boost        — high-signal topic tags (Funding, Research, etc.)
  content_depth    — word count proxy for article substance
  entity_boost     — tier-1 AI company or model mentioned

Formula:
  raw = source_base + title_signals + tag_boost + content_depth + entity_boost
  importance = sigmoid(raw * 4 - 2)   → smooth output in (0, 1)

All inputs are intentionally interpretable; no black-box weighting.
"""
from __future__ import annotations

import math
from typing import Optional


# Source priority (1 = top-tier) → base score
_SOURCE_BASE: dict[int, float] = {
    1: 0.90,
    2: 0.75,
    3: 0.60,
    4: 0.48,
    5: 0.38,
    6: 0.30,
    7: 0.22,
    8: 0.16,
    9: 0.11,
    10: 0.07,
}

# Title words that signal high-importance events
_HIGH_IMPORTANCE_TITLE: list[tuple[str, float]] = [
    # Major events
    ("acqui",       0.20),   # acquires, acquisition
    ("merger",      0.20),
    ("ipo",         0.20),
    ("raises",      0.15),   # fundraising
    ("funding",     0.15),
    ("billion",     0.15),
    ("launches",    0.12),
    ("releases",    0.12),
    ("announces",   0.10),
    ("open source", 0.12),
    ("open-source", 0.12),
    ("regulation",  0.12),
    ("ban",         0.12),
    ("breakthrough",0.15),
    ("first",       0.08),
    ("new model",   0.10),
    ("beats",       0.08),   # benchmark comparisons
    ("surpasses",   0.08),
    ("shutdown",    0.15),
    ("breach",      0.15),
    ("leaked",      0.13),
]

# Tags that lift importance
_HIGH_VALUE_TAGS: dict[str, float] = {
    "Funding":        0.15,
    "Research":       0.12,
    "Open Source":    0.12,
    "Policy":         0.13,
    "Safety":         0.10,
    "Product Launch": 0.10,
    "Acquisition":    0.18,
    "LLM":            0.08,
    "Agent":          0.08,
    "Benchmark":      0.09,
}

# Tier-1 companies that boost any article mentioning them
_TIER1_COMPANIES: frozenset[str] = frozenset({
    "openai", "anthropic", "google deepmind", "meta ai",
    "microsoft", "apple", "amazon", "nvidia",
    "mistral ai", "xai", "inflection ai",
})

# Content depth thresholds
_DEPTH_TIERS: list[tuple[int, float]] = [
    (1200, 0.12),   # long-form (≥1200 words)
    (600,  0.08),   # article (≥600 words)
    (200,  0.04),   # summary (≥200 words)
    (0,    0.00),   # snippet
]


def compute_importance(
    source_priority: int,
    title: str,
    tags: list[str],
    companies: list[str],
    word_count: int,
) -> float:
    """
    Compute importance_score for a single article.

    Args:
        source_priority: int 1–10 (1 = most authoritative)
        title:           article title
        tags:            list of tag names already assigned to the article
        companies:       list of company names already extracted
        word_count:      word count of clean article content

    Returns:
        float in (0.0, 1.0)
    """
    base = _SOURCE_BASE.get(max(1, min(source_priority, 10)), 0.20)

    title_boost = _title_signal(title)
    tag_boost   = _tag_signal(tags)
    depth_boost = _depth_signal(word_count)
    entity_boost = _entity_signal(companies)

    raw = base + title_boost + tag_boost + depth_boost + entity_boost
    return _sigmoid(raw * 2.5 - 1.8)


# ---------------------------------------------------------------------------
# Sub-signal helpers
# ---------------------------------------------------------------------------

def _title_signal(title: str) -> float:
    """Sum keyword boosts found in title, capped at 0.30."""
    lower = title.lower()
    total = 0.0
    for keyword, boost in _HIGH_IMPORTANCE_TITLE:
        if keyword in lower:
            total += boost
    return min(total, 0.30)


def _tag_signal(tags: list[str]) -> float:
    """Sum tag boosts, capped at 0.25."""
    total = sum(_HIGH_VALUE_TAGS.get(tag, 0.0) for tag in tags)
    return min(total, 0.25)


def _depth_signal(word_count: int) -> float:
    for threshold, boost in _DEPTH_TIERS:
        if word_count >= threshold:
            return boost
    return 0.0


def _entity_signal(companies: list[str]) -> float:
    """0.12 if any tier-1 company is mentioned, else 0."""
    lower_names = {c.lower() for c in companies}
    return 0.12 if lower_names & _TIER1_COMPANIES else 0.0


def _sigmoid(x: float) -> float:
    x = max(-500.0, min(500.0, x))
    return 1.0 / (1.0 + math.exp(-x))
