"""
TrendSnapshot — daily snapshot of trend scores for all entities.

Stores one record per (date, entity_type, entity_slug) so we can
query historical trend data and compute velocity.
"""
from __future__ import annotations

from sqlalchemy import Float, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EntityType:
    TAG = "tag"
    COMPANY = "company"
    AI_MODEL = "ai_model"


class TrendSnapshot(Base):
    __tablename__ = "trend_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    # "YYYY-MM-DD"

    entity_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # "tag" | "company" | "ai_model"

    entity_slug: Mapped[str] = mapped_column(String(200), nullable=False)
    entity_name: Mapped[str] = mapped_column(String(200), nullable=False)

    # Raw counts
    count_1d: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    count_7d: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    count_30d: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Prior-period counts for velocity calculation
    count_prev_7d: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # articles from days 8-14 (compared against count_7d for velocity)

    # Computed scores (0.0 – 1.0)
    trend_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    velocity: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    # velocity > 0 = growing, < 0 = shrinking

    # Average importance of articles mentioning this entity today
    avg_importance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    __table_args__ = (
        UniqueConstraint("date", "entity_type", "entity_slug",
                         name="uq_snapshot_date_entity"),
        Index("ix_snapshot_date_type_score",
              "date", "entity_type", "trend_score"),
    )

    def __repr__(self) -> str:
        return (
            f"<TrendSnapshot {self.entity_type}={self.entity_slug!r} "
            f"date={self.date} score={self.trend_score:.3f}>"
        )
