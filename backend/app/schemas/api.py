"""
Complete Pydantic schemas for all API responses.
Single source of truth — imported by all route handlers.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

T = TypeVar("T")


# ── Generic wrappers ──────────────────────────────────────────────────────────

class PaginatedResponse(BaseModel, Generic[T]):
    data: list[T]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_prev: bool

    @classmethod
    def build(
        cls,
        items: list[T],
        total: int,
        page: int,
        page_size: int,
    ) -> "PaginatedResponse[T]":
        return cls(
            data=items,
            total=total,
            page=page,
            page_size=page_size,
            has_next=(page * page_size) < total,
            has_prev=page > 1,
        )


class ErrorResponse(BaseModel):
    error: str
    message: str
    detail: Optional[object] = None


# ── Source ────────────────────────────────────────────────────────────────────

class SourceSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    url: str
    source_type: str
    category: str
    priority: int
    is_active: bool
    consecutive_errors: int
    total_articles_fetched: int
    avg_importance_score: float
    last_fetched_at: Optional[str]


# ── Tag ───────────────────────────────────────────────────────────────────────

class TagSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str
    name: str
    category: str
    trend_score: float
    news_count_7d: int
    news_count_30d: int
    description: Optional[str] = None


# ── Company ───────────────────────────────────────────────────────────────────

class CompanySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str
    name: str
    description: Optional[str] = None
    website: Optional[str] = None
    country: Optional[str] = None
    founded_year: Optional[int] = None
    trend_score: float
    news_count_7d: int
    news_count_30d: int
    is_verified: bool


class CompanyListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str
    name: str
    trend_score: float
    news_count_7d: int
    is_verified: bool


# ── AIModel ───────────────────────────────────────────────────────────────────

class AIModelSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str
    name: str
    description: Optional[str] = None
    release_date: Optional[str] = None
    model_type: Optional[str] = None
    is_open_source: bool
    trend_score: float
    news_count_7d: int


# ── Article ───────────────────────────────────────────────────────────────────

class ArticleListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    title: str
    url: str
    published_at: Optional[datetime]
    summary: Optional[str]
    meta_description: Optional[str]
    image_url: Optional[str]
    author: Optional[str]
    importance_score: float
    freshness_score: float
    trend_score: float
    discussion_score: float
    final_score: float
    is_cluster_representative: bool
    cluster_id: Optional[int]
    word_count: Optional[int]
    tags: list[TagSchema] = []
    companies: list[CompanyListItem] = []


class ArticleDetail(ArticleListItem):
    clean_content: Optional[str] = None
    summary_bullets: list[str] = []
    ai_models: list[AIModelSchema] = []
    llm_model_used: Optional[str] = None
    pipeline_stage: str = ""

    @field_validator("summary_bullets", mode="before")
    @classmethod
    def parse_bullets(cls, v: object) -> list[str]:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return []
        return v if isinstance(v, list) else []


# ── Brief ─────────────────────────────────────────────────────────────────────

class BriefTopStory(BaseModel):
    id: int
    slug: str
    title: str
    summary: Optional[str]
    final_score: float
    published_at: Optional[str]
    image_url: Optional[str] = None


class DailyBriefSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: str
    headline: str
    summary: str
    key_themes: list[str] = []
    is_published: bool
    llm_model_used: Optional[str]
    total_articles_processed: int
    total_articles_published: int
    avg_importance_score: float

    @field_validator("key_themes", mode="before")
    @classmethod
    def parse_themes(cls, v: object) -> list[str]:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return []
        return v if isinstance(v, list) else []


class DailyBriefDetail(DailyBriefSchema):
    top_stories: list[BriefTopStory] = []
    trending_tags: list[TagSchema] = []


# ── Trend ─────────────────────────────────────────────────────────────────────

class TrendTagSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str
    name: str
    category: str
    trend_score: float
    news_count_7d: int
    news_count_30d: int


class TrendCompanySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str
    name: str
    trend_score: float
    news_count_7d: int


class TrendSnapshotSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: str
    entity_type: str
    slug: str
    name: str
    trend_score: float
    velocity: float
    count_1d: int
    count_7d: int
    count_30d: int
    avg_importance: float


# ── Search ────────────────────────────────────────────────────────────────────

class SearchResult(BaseModel):
    articles: list[ArticleListItem]
    total: int
    query: str
    took_ms: float


# ── Stats ─────────────────────────────────────────────────────────────────────

class PlatformStats(BaseModel):
    total_articles: int
    published_articles: int
    total_sources: int
    active_sources: int
    total_tags: int
    total_companies: int
    total_briefs: int
    last_pipeline_run: Optional[str]
    last_pipeline_status: Optional[str]
    articles_today: int
    avg_daily_articles_7d: float


# ── Pipeline ──────────────────────────────────────────────────────────────────

class PipelineRunSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    run_id: str
    date: str
    status: str
    started_at: datetime
    finished_at: Optional[datetime]
    duration_s: Optional[float]
    articles_collected: int
    articles_after_dedup: int
    articles_analyzed: int
    articles_published: int
    llm_input_tokens: int
    llm_output_tokens: int
    llm_cost_usd: float


class PipelineRunDetail(PipelineRunSchema):
    stage_stats: dict = {}
    errors: list[str] = []

    @field_validator("stage_stats", mode="before")
    @classmethod
    def parse_stage_stats(cls, v: object) -> dict:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return {}
        return v if isinstance(v, dict) else {}

    @field_validator("errors", mode="before")
    @classmethod
    def parse_errors(cls, v: object) -> list[str]:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return []
        return v if isinstance(v, list) else []
