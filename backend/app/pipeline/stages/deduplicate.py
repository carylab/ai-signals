"""
Stage: deduplicate

Two-pass deduplication:
  Pass 1 — exact URL hash check against DB (O(1) per article)
  Pass 2 — SimHash near-duplicate detection within the current batch
            (catches same story from multiple sources)

Articles flagged as duplicates are removed from ctx.articles.
"""
from __future__ import annotations

from typing import Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.pipeline.base import PipelineContext, PipelineStageBase
from app.models.news import NewsArticle

logger = structlog.get_logger(__name__)


class DeduplicateStage(PipelineStageBase):
    name = "deduplicate"

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def process(self, ctx: PipelineContext) -> PipelineContext:
        before = len(ctx.articles)

        # Pass 1: check url_hash against DB
        ctx.articles = await self._dedup_by_url(ctx.articles, ctx)

        # Pass 2: SimHash within-batch dedup
        ctx.articles = _dedup_by_simhash(ctx.articles, ctx)

        after = len(ctx.articles)
        ctx.set_stage_stat(self.name, "before", before)
        ctx.set_stage_stat(self.name, "after", after)
        ctx.set_stage_stat(self.name, "removed", before - after)
        return ctx

    async def _dedup_by_url(
        self, articles: list[dict], ctx: PipelineContext
    ) -> list[dict]:
        """Remove articles whose url_hash already exists in DB."""
        hashes = [a["url_hash"] for a in articles if a.get("url_hash")]
        if not hashes:
            return articles

        result = await self._session.execute(
            select(NewsArticle.url_hash).where(
                NewsArticle.url_hash.in_(hashes)
            )
        )
        existing: set[str] = {row[0] for row in result.fetchall()}

        kept = [a for a in articles if a.get("url_hash") not in existing]
        ctx.set_stage_stat(self.name, "url_dedup_removed", len(articles) - len(kept))
        return kept


# ---------------------------------------------------------------------------
# SimHash implementation (no external dependency)
# ---------------------------------------------------------------------------

def _simhash(text: str, bits: int = 64) -> int:
    """Compute a SimHash fingerprint for text."""
    import hashlib

    tokens = text.lower().split()
    v = [0] * bits

    for token in tokens:
        h = int(hashlib.md5(token.encode()).hexdigest(), 16)  # noqa: S324
        for i in range(bits):
            if h & (1 << i):
                v[i] += 1
            else:
                v[i] -= 1

    fingerprint = 0
    for i in range(bits):
        if v[i] > 0:
            fingerprint |= 1 << i
    return fingerprint


def _hamming_distance(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def _dedup_by_simhash(
    articles: list[dict],
    ctx: PipelineContext,
    threshold: int = 6,  # bits differing; ~90% similarity for 64-bit hash
) -> list[dict]:
    """
    Within-batch near-duplicate detection.
    O(n²) but n is at most ~500 articles per run — acceptable.
    For larger scale, use a proper LSH index (Step 8 / V2).
    """
    kept: list[dict] = []
    seen_hashes: list[int] = []
    removed = 0

    for article in articles:
        text = f"{article.get('title', '')} {article.get('clean_content', '')[:500]}"
        sh = _simhash(text)
        article["sim_hash"] = format(sh, "016x")

        is_dup = any(
            _hamming_distance(sh, seen) <= threshold
            for seen in seen_hashes
        )

        if is_dup:
            removed += 1
        else:
            seen_hashes.append(sh)
            kept.append(article)

    ctx.set_stage_stat(ctx.stats.get("deduplicate", {}).get("name", "deduplicate"),
                       "simhash_removed", removed)
    # Simpler direct write:
    ctx.stats.setdefault("deduplicate", {})["simhash_removed"] = removed
    return kept
