"""
Top-level API router.
All v1 sub-routers are mounted here with consistent prefixes and tags.
"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import (
    briefs,
    companies,
    news,
    pipeline,
    rss,
    search,
    stats,
    topics,
    trends,
)

api_router = APIRouter()

# ── Public endpoints ──────────────────────────────────────────────────────────
api_router.include_router(news.router,       prefix="/v1/news",       tags=["News"])
api_router.include_router(briefs.router,     prefix="/v1/briefs",     tags=["Briefs"])
api_router.include_router(trends.router,     prefix="/v1/trends",     tags=["Trends"])
api_router.include_router(topics.router,     prefix="/v1/topics",     tags=["Topics"])
api_router.include_router(companies.router,  prefix="/v1/companies",  tags=["Companies"])
api_router.include_router(search.router,     prefix="/v1/search",     tags=["Search"])
api_router.include_router(rss.router,        prefix="/v1/rss",        tags=["RSS"])
api_router.include_router(stats.router,      prefix="/v1/stats",      tags=["Stats"])

# ── Internal / ops endpoints ──────────────────────────────────────────────────
api_router.include_router(pipeline.router,   prefix="/v1/pipeline",   tags=["Pipeline"])
