"""
Database engine, session management, and base model.
Supports SQLite (dev) and PostgreSQL (prod) via DATABASE_URL.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import AsyncGenerator

from sqlalchemy import DateTime, MetaData, event, text
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Naming convention ensures Alembic can auto-generate constraint names
# for both SQLite and PostgreSQL.
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(AsyncAttrs, DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)

    # All tables get created_at / updated_at automatically
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


# ---------------------------------------------------------------------------
# Engine factory
# ---------------------------------------------------------------------------

def _build_engine(database_url: str):
    """
    Create async engine.

    SQLite:     sqlite+aiosqlite:///./data/db/ai_signals.db
    PostgreSQL: postgresql+asyncpg://user:pass@host:5432/dbname
    """
    connect_args: dict = {}
    engine_kwargs: dict = {}

    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        engine_kwargs["pool_pre_ping"] = True
    else:
        # PostgreSQL connection pool settings
        engine_kwargs.update(
            {
                "pool_size": 5,
                "max_overflow": 10,
                "pool_pre_ping": True,
                "pool_recycle": 3600,
            }
        )

    engine = create_async_engine(
        database_url,
        connect_args=connect_args,
        echo=False,           # set True for SQL debug logging
        future=True,
        **engine_kwargs,
    )

    # Enable WAL mode and foreign keys for SQLite
    if database_url.startswith("sqlite"):
        @event.listens_for(engine.sync_engine, "connect")
        def set_sqlite_pragma(dbapi_conn, _connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.close()

    return engine


# ---------------------------------------------------------------------------
# Module-level singletons (initialised in lifespan)
# ---------------------------------------------------------------------------

_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_db(database_url: str) -> None:
    """Call once at application startup."""
    global _engine, _session_factory
    _engine = _build_engine(database_url)
    _session_factory = async_sessionmaker(
        _engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )


def get_engine():
    if _engine is None:
        raise RuntimeError("Database not initialised. Call init_db() first.")
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    if _session_factory is None:
        raise RuntimeError("Database not initialised. Call init_db() first.")
    return _session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency."""
    if _session_factory is None:
        raise RuntimeError("Database not initialised. Call init_db() first.")
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def create_all_tables() -> None:
    """Create all tables. Used in dev/test; prod uses Alembic migrations."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_all_tables() -> None:
    """Drop all tables. Test use only."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
