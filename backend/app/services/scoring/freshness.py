"""
Freshness Score  (0.0 – 1.0)

Time-decay model: score starts at 1.0 when published and
decays exponentially with a configurable half-life.

Default half-life: 24 hours.
  Age  0h → 1.000
  Age  6h → 0.841
  Age 12h → 0.707
  Age 24h → 0.500  ← half-life
  Age 48h → 0.250
  Age 72h → 0.125
  Age  7d → 0.005

Articles older than max_age_hours receive score = 0.0
(they still appear in search / archives but not in "fresh" rankings).

Formula:
  score = exp(-λ × age_hours)
  where λ = ln(2) / half_life_hours
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Optional

# Default decay parameters
_HALF_LIFE_HOURS: float = 24.0
_MAX_AGE_HOURS: float   = 7 * 24   # 7 days


def compute_freshness(
    published_at: Optional[datetime | str],
    now: Optional[datetime] = None,
    half_life_hours: float = _HALF_LIFE_HOURS,
    max_age_hours: float = _MAX_AGE_HOURS,
) -> float:
    """
    Compute freshness_score for a single article.

    Args:
        published_at:     publication datetime (aware or naive UTC),
                          or ISO string, or None
        now:              reference point for age calculation
                          (defaults to datetime.now(UTC))
        half_life_hours:  hours after which score halves
        max_age_hours:    articles older than this get score 0.0

    Returns:
        float in [0.0, 1.0]
    """
    reference = now or datetime.now(timezone.utc)
    pub = _parse_datetime(published_at)

    if pub is None:
        # Unknown publish time — assign a mild penalty
        return 0.40

    if pub.tzinfo is None:
        pub = pub.replace(tzinfo=timezone.utc)

    age_hours = (reference - pub).total_seconds() / 3600.0

    # Future-dated articles (clock skew from sources) treated as "just now"
    age_hours = max(0.0, age_hours)

    if age_hours >= max_age_hours:
        return 0.0

    lam = math.log(2.0) / half_life_hours
    return round(math.exp(-lam * age_hours), 6)


def freshness_at_age(age_hours: float, half_life_hours: float = _HALF_LIFE_HOURS) -> float:
    """Utility: compute the freshness score for a given age in hours."""
    if age_hours < 0:
        return 1.0
    lam = math.log(2.0) / half_life_hours
    return round(math.exp(-lam * age_hours), 6)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_datetime(value: Optional[datetime | str]) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
        # Try ISO 8601 variants
        for fmt in (
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
        ):
            try:
                dt = datetime.strptime(value[:25], fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                continue
    return None
