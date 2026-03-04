"""
FastAPI dependency functions.

Injected into route handlers via Depends():
    async def my_route(db: DbSession, llm: LLMClient): ...
"""
from __future__ import annotations

from typing import Annotated, AsyncGenerator

import structlog
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings, Settings
from app.core.database import get_session

logger = structlog.get_logger(__name__)


# ── Settings ──────────────────────────────────────────────────────────────────

def settings_dep() -> Settings:
    return get_settings()


AppSettings = Annotated[Settings, Depends(settings_dep)]


# ── Database session ──────────────────────────────────────────────────────────

DbSession = Annotated[AsyncSession, Depends(get_session)]


# ── LLM client ────────────────────────────────────────────────────────────────

def get_llm_client():
    """
    Return the configured LLM client instance.
    The factory reads LLM_PROVIDER and the corresponding API key from settings.
    """
    from app.services.llm.factory import create_llm_client
    return create_llm_client()


LLMClient = Annotated[object, Depends(get_llm_client)]


# ── Pagination ────────────────────────────────────────────────────────────────

from dataclasses import dataclass


@dataclass
class Pagination:
    page: int = 1
    page_size: int = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


def pagination_dep(
    page: int = 1,
    page_size: int = 20,
    cfg: Settings = Depends(settings_dep),
) -> Pagination:
    page = max(1, page)
    page_size = max(1, min(page_size, cfg.api_max_page_size))
    return Pagination(page=page, page_size=page_size)


PaginationDep = Annotated[Pagination, Depends(pagination_dep)]
