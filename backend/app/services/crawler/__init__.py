"""
Shared types for all crawler modules.

RawArticle is the output contract every fetcher must produce.
It maps directly to the article dict flowing through the pipeline.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class RawArticle:
    """
    Minimal article data returned by any fetcher.
    The pipeline's Extract stage will enrich this further.
    """
    url: str
    title: str
    source_id: int
    source_slug: str
    source_priority: int = 5

    published_at: Optional[datetime] = None
    raw_content: str = ""          # HTML or plain text from feed/scrape
    author: str = ""
    image_url: Optional[str] = None
    fetch_error: Optional[str] = None
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "title": self.title,
            "source_id": self.source_id,
            "source_slug": self.source_slug,
            "source_priority": self.source_priority,
            "published_at": self.published_at,
            "raw_content": self.raw_content,
            "author": self.author,
            "image_url": self.image_url,
            "fetch_error": self.fetch_error,
            **self.extra,
        }
