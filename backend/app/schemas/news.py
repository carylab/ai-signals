"""
Schemas for NewsArticle API responses.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


class TagSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str
    name: str
    trend_score: float = 0.0


class CompanySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str
    name: str
    trend_score: float = 0.0


class AIModelSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str
    name: str


class ArticleListItem(BaseModel):
    """Compact article representation for list/index endpoints."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    title: str
    url: str
    published_at: Optional[datetime]
    summary: Optional[str]
    meta_description: Optional[str]
    image_url: Optional[str]
    importance_score: float
    final_score: float
    is_cluster_representative: bool
    cluster_id: Optional[int]
    tags: list[TagSchema] = []
    companies: list[CompanySchema] = []


class ArticleDetail(ArticleListItem):
    """Full article detail with all fields."""
    clean_content: Optional[str]
    summary_bullets: list[str] = []
    ai_models: list[AIModelSchema] = []
    word_count: Optional[int]
    author: Optional[str]
    freshness_score: float
    trend_score: float
    discussion_score: float
    llm_model_used: Optional[str]

    @field_validator("summary_bullets", mode="before")
    @classmethod
    def parse_bullets(cls, v: object) -> list[str]:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return []
        if isinstance(v, list):
            return v
        return []


class ArticleSearchParams(BaseModel):
    """Query parameters for article search/filter."""
    q: Optional[str] = None          # full-text search
    tag: Optional[str] = None        # filter by tag slug
    company: Optional[str] = None    # filter by company slug
    date: Optional[str] = None       # YYYY-MM-DD
    min_score: float = 0.0
