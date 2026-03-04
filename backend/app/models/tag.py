"""
Tag — topic/category label attached to news articles.
"""
from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.news import NewsArticle


class TagCategory(str):
    TECHNOLOGY = "technology"   # LLM, Agent, RAG, Infra
    BUSINESS = "business"       # Funding, Startup, M&A
    POLICY = "policy"           # Regulation, Safety, Gov
    RESEARCH = "research"       # Paper, Benchmark, Dataset
    OPEN_SOURCE = "open_source"


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(30), nullable=False, default="technology")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Trend metrics (updated daily by trend engine)
    news_count_7d: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    news_count_30d: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    trend_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    # trend_score: velocity of growth vs. prior period

    # Relationships
    articles: Mapped[list["NewsArticle"]] = relationship(
        secondary="article_tags", back_populates="tags", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<Tag slug={self.slug!r} trend={self.trend_score:.2f}>"
