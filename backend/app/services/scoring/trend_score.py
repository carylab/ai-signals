"""
Trend Score  (0.0 – 1.0)

Measures how much an article's tags and entities are currently trending.

Inputs:
  - article's tag list
  - article's company list
  - article's ai_model list
  - pre-loaded trend scores from DB (slug → score mapping)

Formula:
  max(
      max(tag_trend_scores),
      max(company_trend_scores) × 0.85,   ← companies weighted slightly lower
      max(model_trend_scores)   × 0.85,
  )

Taking the max (not average) means: if an article mentions any hot
topic, it rides that wave — even if other tags are cold.

The 0.85 weight on companies/models prevents a company's perpetual
brand value from overriding genuine daily topic trends.
"""
from __future__ import annotations


# Weight applied to company/model trend scores
_ENTITY_WEIGHT = 0.85


def compute_trend(
    tags: list[str],
    companies: list[str],
    ai_models: list[str],
    tag_trend_scores: dict[str, float],
    company_trend_scores: dict[str, float],
    model_trend_scores: dict[str, float],
) -> float:
    """
    Compute trend_score for a single article.

    Args:
        tags:                 tag names on this article
        companies:            company names on this article
        ai_models:            AI model names on this article
        tag_trend_scores:     {tag_slug: trend_score}  pre-loaded from DB
        company_trend_scores: {company_slug: trend_score}
        model_trend_scores:   {model_slug: trend_score}

    Returns:
        float in [0.0, 1.0]
    """
    candidate_scores: list[float] = [0.0]

    # Tag trend
    for tag in tags:
        slug = _to_slug(tag)
        score = tag_trend_scores.get(slug, 0.0)
        candidate_scores.append(score)

    # Company trend (weighted down slightly)
    for company in companies:
        slug = _to_slug(company)
        score = company_trend_scores.get(slug, 0.0) * _ENTITY_WEIGHT
        candidate_scores.append(score)

    # AI model trend (weighted down slightly)
    for model in ai_models:
        slug = _to_slug(model)
        score = model_trend_scores.get(slug, 0.0) * _ENTITY_WEIGHT
        candidate_scores.append(score)

    return round(max(candidate_scores), 6)


def _to_slug(name: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
