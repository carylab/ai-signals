"""
RSS Fetcher — primary article source.

Fetches and parses RSS/Atom feeds using feedparser.
Falls back to fetching raw HTML via httpx when feedparser
cannot retrieve the feed directly (e.g. requires headers).

Output: list[dict]  (each dict matches RawArticle.to_dict() shape)
"""
from __future__ import annotations

import asyncio
import email.utils
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

import feedparser
import structlog

from app.services.crawler import RawArticle
from app.services.crawler.http_client import fetch_url

logger = structlog.get_logger(__name__)

# feedparser is synchronous — run in executor to avoid blocking event loop
_FEEDPARSER_TIMEOUT = 20  # seconds passed to feedparser


class RSSFetcher:
    """Fetch articles from a NewsSource via its RSS/Atom feed URL."""

    async def fetch(self, source) -> list[dict]:
        """
        Args:
            source: NewsSource ORM object with .feed_url, .id, .slug, .priority

        Returns:
            list of raw article dicts ready for the pipeline
        """
        feed_url: str = source.feed_url
        log = logger.bind(source=source.slug, feed_url=feed_url)

        try:
            feed = await self._parse_feed(feed_url)
        except Exception as exc:
            log.error("rss_feed_error", error=str(exc))
            raise

        if feed.bozo and not feed.entries:
            # bozo=True means feedparser found a malformed feed
            log.warning(
                "rss_feed_bozo",
                bozo_exception=str(getattr(feed, "bozo_exception", "")),
            )

        articles: list[dict] = []
        for entry in feed.entries:
            article = self._parse_entry(entry, source)
            if article:
                articles.append(article.to_dict())

        log.info("rss_fetched", count=len(articles))
        return articles

    async def _parse_feed(self, feed_url: str) -> feedparser.FeedParserDict:
        """
        Parse feed asynchronously.
        feedparser.parse() is synchronous and does its own HTTP — we pass
        the raw bytes so we can use our own HTTP client with proper headers.
        """
        loop = asyncio.get_event_loop()

        try:
            # Fetch raw bytes via our controlled HTTP client
            response = await fetch_url(feed_url)
            raw_bytes = response.content
            content_type = response.headers.get("content-type", "")

            # Parse from bytes in executor (feedparser is CPU-bound for large feeds)
            feed = await loop.run_in_executor(
                None,
                lambda: feedparser.parse(
                    raw_bytes,
                    response_headers={"content-type": content_type},
                ),
            )
            return feed

        except Exception:
            # Last resort: let feedparser handle its own HTTP
            # (useful for feeds that need special negotiation)
            logger.debug("rss_fallback_feedparser_http", url=feed_url)
            feed = await loop.run_in_executor(
                None,
                lambda: feedparser.parse(feed_url),
            )
            return feed

    def _parse_entry(self, entry: feedparser.FeedParserDict, source) -> Optional[RawArticle]:
        """Convert a feedparser entry to a RawArticle."""
        # URL
        url = entry.get("link") or entry.get("id", "")
        if not url or not url.startswith("http"):
            return None

        # Title
        title = _clean_field(entry.get("title", ""))
        if not title:
            return None

        # Published date
        published_at = _parse_date(entry)

        # Content / summary
        raw_content = _extract_content(entry)

        # Author
        author = ""
        if entry.get("author"):
            author = str(entry.author)
        elif entry.get("authors"):
            author = ", ".join(
                a.get("name", "") for a in entry.authors if a.get("name")
            )

        # Image — check media:content and enclosures
        image_url = _extract_image(entry)

        return RawArticle(
            url=url,
            title=title,
            source_id=source.id,
            source_slug=source.slug,
            source_priority=source.priority,
            published_at=published_at,
            raw_content=raw_content,
            author=author,
            image_url=image_url,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clean_field(value: str) -> str:
    """Strip HTML tags and extra whitespace from a feed field."""
    import re
    text = re.sub(r"<[^>]+>", " ", value)
    return " ".join(text.split()).strip()


def _parse_date(entry: feedparser.FeedParserDict) -> Optional[datetime]:
    """Extract and normalise publish date from a feed entry."""
    # feedparser normalises to time.struct_time in entry.published_parsed
    for attr in ("published_parsed", "updated_parsed", "created_parsed"):
        t = getattr(entry, attr, None)
        if t:
            try:
                return datetime(*t[:6], tzinfo=timezone.utc)
            except (TypeError, ValueError):
                continue

    # Fallback: parse raw string
    for attr in ("published", "updated", "created"):
        raw = getattr(entry, attr, None)
        if raw:
            try:
                parsed = email.utils.parsedate_to_datetime(raw)
                return parsed.astimezone(timezone.utc)
            except Exception:
                continue

    return None


def _extract_content(entry: feedparser.FeedParserDict) -> str:
    """
    Extract the richest content available from a feed entry.
    Priority: content[0] > summary > title
    """
    # content field (full article HTML in some feeds)
    if hasattr(entry, "content") and entry.content:
        for c in entry.content:
            if c.get("value"):
                return c["value"]

    # summary / description
    if entry.get("summary"):
        return entry.summary

    return ""


def _extract_image(entry: feedparser.FeedParserDict) -> Optional[str]:
    """Try to find a representative image URL in the entry."""
    # media:content (most common)
    media = getattr(entry, "media_content", [])
    for m in (media or []):
        if m.get("url") and m.get("medium") in ("image", None):
            url = m["url"]
            if _looks_like_image(url):
                return url

    # enclosures
    for enc in (getattr(entry, "enclosures", None) or []):
        if enc.get("type", "").startswith("image/"):
            return enc.get("href") or enc.get("url")

    # og:image style links
    for link in (getattr(entry, "links", None) or []):
        if "image" in link.get("type", "") and link.get("href"):
            return link["href"]

    return None


def _looks_like_image(url: str) -> bool:
    path = urlparse(url).path.lower()
    return any(path.endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif"))
