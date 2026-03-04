"""
Shared response schemas used across multiple API endpoints.
"""
from __future__ import annotations

from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """Standard envelope for all API responses."""
    data: T
    meta: Optional[dict] = None


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated list response."""
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
