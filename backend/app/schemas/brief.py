"""
Schemas for DailyBrief API responses.
"""
from __future__ import annotations

import json
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

from app.schemas.news import ArticleListItem


class BriefTopStory(BaseModel):
    id: int
    slug: str
    title: str
    summary: Optional[str]
    final_score: float
    published_at: Optional[str]


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

    @field_validator("key_themes", mode="before")
    @classmethod
    def parse_themes(cls, v: object) -> list[str]:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return []
        return v or []


class DailyBriefDetail(DailyBriefSchema):
    """Full brief with embedded top stories."""
    top_stories: list[BriefTopStory] = []
    trending_tag_slugs: list[str] = []
