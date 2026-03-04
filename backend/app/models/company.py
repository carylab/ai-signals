"""
Company — AI company entity extracted/recognised from news.
AIModel  — AI model entity linked to a company.
"""
from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.news import NewsArticle


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    founded_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Auto-generated flag — company page created automatically from news mentions
    is_auto_generated: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Trend metrics
    news_count_7d: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    news_count_30d: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    trend_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Relationships
    ai_models: Mapped[list["AIModel"]] = relationship(
        back_populates="company", lazy="select"
    )
    articles: Mapped[list["NewsArticle"]] = relationship(
        secondary="article_companies", back_populates="companies", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<Company slug={self.slug!r}>"


class AIModel(Base):
    __tablename__ = "ai_models"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    release_date: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    company_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True
    )
    company: Mapped[Optional["Company"]] = relationship(
        back_populates="ai_models", lazy="select"
    )

    model_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )
    # e.g. "LLM", "Image", "Video", "Audio", "Multimodal"

    is_open_source: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_auto_generated: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    news_count_7d: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    trend_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    articles: Mapped[list["NewsArticle"]] = relationship(
        secondary="article_models", back_populates="ai_models", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<AIModel slug={self.slug!r} company={self.company_id}>"
