"""
Integration tests for the FastAPI application.
Uses httpx.AsyncClient with ASGITransport — no real HTTP, no real DB calls
(test DB is in-memory SQLite from conftest.py).
"""
from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    """Return an async test client bound to the FastAPI app."""
    # Import app after env vars are set by conftest
    from app.main import create_app
    application = create_app()

    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="http://test",
    ) as ac:
        yield ac


# ── Health ─────────────────────────────────────────────────────────────────────

class TestHealth:
    @pytest.mark.asyncio
    async def test_health_ok(self, client: AsyncClient) -> None:
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    @pytest.mark.asyncio
    async def test_root_ok(self, client: AsyncClient) -> None:
        resp = await client.get("/")
        assert resp.status_code == 200


# ── News ───────────────────────────────────────────────────────────────────────

class TestNewsEndpoints:
    @pytest.mark.asyncio
    async def test_list_articles_empty(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/news")
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert "total" in data
        assert isinstance(data["data"], list)

    @pytest.mark.asyncio
    async def test_list_articles_pagination(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/news?page=1&page_size=5")
        assert resp.status_code == 200
        data = resp.json()
        assert data["page"] == 1
        assert data["page_size"] == 5

    @pytest.mark.asyncio
    async def test_article_not_found(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/news/nonexistent-slug")
        assert resp.status_code == 404
        assert resp.json()["error"] == "NotFoundError"

    @pytest.mark.asyncio
    async def test_top_articles(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/news/top?limit=5")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ── Briefs ─────────────────────────────────────────────────────────────────────

class TestBriefEndpoints:
    @pytest.mark.asyncio
    async def test_list_briefs_empty(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/briefs")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    @pytest.mark.asyncio
    async def test_latest_brief_not_found(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/briefs/latest")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_brief_by_date_not_found(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/briefs/2026-01-01")
        assert resp.status_code == 404


# ── Trends ─────────────────────────────────────────────────────────────────────

class TestTrendEndpoints:
    @pytest.mark.asyncio
    async def test_trending_tags(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/trends/tags")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_trending_companies(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/trends/companies")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_trending_models(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/trends/models")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_trend_history_empty(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/trends/history/tag/llm")
        assert resp.status_code == 200
        assert resp.json() == []


# ── Search ─────────────────────────────────────────────────────────────────────

class TestSearchEndpoints:
    @pytest.mark.asyncio
    async def test_search_returns_structure(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/search?q=openai")
        assert resp.status_code == 200
        data = resp.json()
        assert "articles" in data
        assert "total" in data
        assert "query" in data
        assert data["query"] == "openai"

    @pytest.mark.asyncio
    async def test_search_too_short(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/search?q=a")
        # FastAPI validation rejects queries shorter than min_length=2
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_search_with_tag_filter(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/search?q=AI&tag=llm")
        assert resp.status_code == 200


# ── Stats ──────────────────────────────────────────────────────────────────────

class TestStatsEndpoints:
    @pytest.mark.asyncio
    async def test_platform_stats(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_articles" in data
        assert "active_sources" in data
        assert "last_pipeline_run" in data

    @pytest.mark.asyncio
    async def test_source_stats(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/stats/sources")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ── RSS ────────────────────────────────────────────────────────────────────────

class TestRSSEndpoints:
    @pytest.mark.asyncio
    async def test_main_rss_feed(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/rss")
        assert resp.status_code == 200
        assert "application/rss+xml" in resp.headers["content-type"]
        assert "<?xml" in resp.text
        assert "<rss" in resp.text

    @pytest.mark.asyncio
    async def test_daily_rss_feed(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/rss/daily")
        assert resp.status_code == 200
        assert "rss" in resp.text

    @pytest.mark.asyncio
    async def test_tag_rss_feed(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/rss/tag/llm")
        assert resp.status_code == 200
        assert "rss" in resp.text


# ── Pipeline (internal) ────────────────────────────────────────────────────────

class TestPipelineEndpoints:
    @pytest.mark.asyncio
    async def test_list_runs_empty(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/pipeline/runs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_run_not_found(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/pipeline/runs/nonexistent-run-id")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_list_sources(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/pipeline/sources")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
