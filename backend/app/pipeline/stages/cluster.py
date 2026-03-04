"""
Stage: cluster

Groups articles that cover the same story into clusters.
Uses SimHash Hamming distance (same fingerprints already computed
in deduplication stage) so no extra embedding calls needed for MVP.

Each cluster gets an integer ID.  The article with the highest
source priority becomes the cluster representative.

V2 upgrade path: replace with sentence-transformer embeddings + DBSCAN.
"""
from __future__ import annotations

import structlog

from app.pipeline.base import PipelineContext, PipelineStageBase

logger = structlog.get_logger(__name__)

_CLUSTER_THRESHOLD = 10   # bits — looser than dedup (catches same story, not copies)


class ClusterStage(PipelineStageBase):
    name = "cluster"

    async def process(self, ctx: PipelineContext) -> PipelineContext:
        articles = ctx.articles
        if not articles:
            return ctx

        clusters = _build_clusters(articles)

        # Assign cluster_id and representative flag
        for cluster_id, members in enumerate(clusters):
            # Representative = highest-priority source (lowest priority number)
            rep = min(members, key=lambda a: a.get("source_priority", 5))
            for a in members:
                a["cluster_id"] = cluster_id
                a["is_cluster_representative"] = (a is rep)

        ctx.articles = articles
        ctx.set_stage_stat(self.name, "clusters_found", len(clusters))
        ctx.set_stage_stat(self.name, "articles_in", len(articles))

        singletons = sum(1 for c in clusters if len(c) == 1)
        ctx.set_stage_stat(self.name, "singleton_clusters", singletons)
        ctx.set_stage_stat(self.name, "multi_clusters", len(clusters) - singletons)

        return ctx


def _build_clusters(articles: list[dict]) -> list[list[dict]]:
    """
    Union-Find clustering by SimHash distance.
    Articles within _CLUSTER_THRESHOLD bits of each other are merged.
    """
    n = len(articles)
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: int, y: int) -> None:
        parent[find(x)] = find(y)

    # Parse stored sim_hashes
    hashes: list[int] = []
    for a in articles:
        sh_str = a.get("sim_hash", "0")
        try:
            hashes.append(int(sh_str, 16))
        except (ValueError, TypeError):
            hashes.append(0)

    # O(n²) — acceptable for n ≤ 500
    for i in range(n):
        for j in range(i + 1, n):
            if _hamming(hashes[i], hashes[j]) <= _CLUSTER_THRESHOLD:
                union(i, j)

    # Group by root
    groups: dict[int, list[dict]] = {}
    for i, article in enumerate(articles):
        root = find(i)
        groups.setdefault(root, []).append(article)

    return list(groups.values())


def _hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")
