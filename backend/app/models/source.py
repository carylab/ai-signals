"""
NewsSource — represents an RSS feed or scrapable website.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SourceType(str, Enum):
    RSS = "rss"
    SCRAPE = "scrape"
    API = "api"


class SourceCategory(str, Enum):
    MEDIA = "media"           # TechCrunch, Wired
    RESEARCH = "research"     # ArXiv, Google AI Blog
    COMPANY = "company"       # OpenAI Blog, Anthropic Blog
    COMMUNITY = "community"   # HN, Reddit
    FINANCE = "finance"       # Crunchbase, Bloomberg


class NewsSource(Base):
    __tablename__ = "news_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), unique=True, nullable=False, index=True)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    feed_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)

    source_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default=SourceType.RSS
    )
    category: Mapped[str] = mapped_column(
        String(30), nullable=False, default=SourceCategory.MEDIA
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    # 1 (highest) – 10 (lowest); affects importance_score base

    # Health tracking
    last_fetched_at: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    consecutive_errors: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_articles_fetched: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Quality signals
    avg_importance_score: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)

    # Relationships
    articles: Mapped[list["NewsArticle"]] = relationship(  # noqa: F821
        back_populates="source", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<NewsSource id={self.id} slug={self.slug!r}>"
