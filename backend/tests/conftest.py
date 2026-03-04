"""
conftest.py — shared pytest fixtures for the backend test suite.
"""
from __future__ import annotations

import asyncio
import os
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

# Use in-memory SQLite for tests — no file I/O
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("LLM_PROVIDER", "openai")
os.environ.setdefault("OPENAI_API_KEY", "test-key-not-used")


@pytest.fixture(scope="session")
def event_loop():
    """Single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def db_engine():
    from app.config import settings
    from app.core.database import init_db, create_all_tables, get_engine

    init_db(settings.database_url)
    await create_all_tables()
    yield get_engine()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Per-test database session that rolls back after each test."""
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.rollback()
