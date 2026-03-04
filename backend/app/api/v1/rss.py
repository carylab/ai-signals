"""
RSS feed generator.

Produces valid RSS 2.0 XML for:
  /api/v1/rss              — top 50 latest articles
  /api/v1/rss/daily        — daily briefs
  /api/v1/rss/tag/{slug}   — articles for a specific topic

The XML is generated manually (no external library) to keep
dependencies minimal and output format fully controlled.
"""
from __future__ import annotations

import html
import textwrap
from datetime import datetime, timezone
from email.utils import format_datetime
from typing import Optional

import structlog
from fastapi import APIRouter
from fastapi.responses import Response
from sqlalchemy import desc, select

from app.config import settings
from app.dependencies import DbSession
from app.models.news import NewsArticle
from app.models.brief import DailyBrief
from app.models.tag import Tag

router = APIRouter()
logger = structlog.get_logger(__name__)

_SITE_URL = "https://aisignals.io"
_FEED_TTL = 60   # minutes

RSS_CONTENT_TYPE = "application/rss+xml; charset=utf-8"


@router.get("", response_class=Response)
async def rss_feed(db: DbSession) -> Response:
    """Main RSS feed — top 50 published articles by final_score."""
    articles = (
        await db.execute(
            select(NewsArticle)
            .where(
                NewsArticle.is_published.is_(True),
                NewsArticle.is_cluster_representative.is_(True),
            )
            .order_by(desc(NewsArticle.published_at))
            .limit(50)
        )
    ).scalars().all()

    items = [_article_to_item(a) for a in articles]
    xml = _build_feed(
        title="AI Signals — Latest AI News",
        link=_SITE_URL,
        description="Daily AI industry intelligence. Top AI news, trends, and analysis.",
        feed_url=f"{_SITE_URL}/api/v1/rss",
        items=items,
    )
    return Response(content=xml, media_type=RSS_CONTENT_TYPE)


@router.get("/daily", response_class=Response)
async def rss_daily_briefs(db: DbSession) -> Response:
    """RSS feed of daily AI briefs."""
    briefs = (
        await db.execute(
            select(DailyBrief)
            .where(DailyBrief.is_published.is_(True))
            .order_by(desc(DailyBrief.date))
            .limit(30)
        )
    ).scalars().all()

    items = [_brief_to_item(b) for b in briefs]
    xml = _build_feed(
        title="AI Signals — Daily AI Briefs",
        link=f"{_SITE_URL}/daily",
        description="Daily AI intelligence briefings — curated summaries of the most important AI news.",
        feed_url=f"{_SITE_URL}/api/v1/rss/daily",
        items=items,
    )
    return Response(content=xml, media_type=RSS_CONTENT_TYPE)


@router.get("/tag/{slug}", response_class=Response)
async def rss_tag_feed(slug: str, db: DbSession) -> Response:
    """RSS feed for a specific topic/tag."""
    tag = await db.scalar(select(Tag).where(Tag.slug == slug))
    tag_name = tag.name if tag else slug

    articles = (
        await db.execute(
            select(NewsArticle)
            .join(NewsArticle.tags)
            .where(
                Tag.slug == slug,
                NewsArticle.is_published.is_(True),
                NewsArticle.is_cluster_representative.is_(True),
            )
            .order_by(desc(NewsArticle.published_at))
            .limit(50)
        )
    ).scalars().unique().all()

    items = [_article_to_item(a) for a in articles]
    xml = _build_feed(
        title=f"AI Signals — {tag_name} News",
        link=f"{_SITE_URL}/topics/{slug}",
        description=f"Latest AI news tagged with {tag_name}.",
        feed_url=f"{_SITE_URL}/api/v1/rss/tag/{slug}",
        items=items,
    )
    return Response(content=xml, media_type=RSS_CONTENT_TYPE)


# ---------------------------------------------------------------------------
# RSS XML builders
# ---------------------------------------------------------------------------

def _build_feed(
    title: str,
    link: str,
    description: str,
    feed_url: str,
    items: list[str],
) -> str:
    now_rfc = format_datetime(datetime.now(timezone.utc))
    items_xml = "\n".join(items)

    return textwrap.dedent(f"""\
        <?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0"
             xmlns:atom="http://www.w3.org/2005/Atom"
             xmlns:content="http://purl.org/rss/1.0/modules/content/">
          <channel>
            <title>{_esc(title)}</title>
            <link>{_esc(link)}</link>
            <description>{_esc(description)}</description>
            <language>en-us</language>
            <lastBuildDate>{now_rfc}</lastBuildDate>
            <ttl>{_FEED_TTL}</ttl>
            <atom:link href="{_esc(feed_url)}" rel="self" type="application/rss+xml"/>
            <image>
              <url>{_SITE_URL}/logo.png</url>
              <title>{_esc(title)}</title>
              <link>{_esc(link)}</link>
            </image>
        {items_xml}
          </channel>
        </rss>""")


def _article_to_item(a: NewsArticle) -> str:
    pub_date = (
        format_datetime(a.published_at)
        if a.published_at
        else format_datetime(datetime.now(timezone.utc))
    )
    article_url = f"{_SITE_URL}/news/{a.slug}"
    summary = _esc(a.summary or a.meta_description or "")
    image_tag = (
        f"\n      <enclosure url=\"{_esc(a.image_url)}\" type=\"image/jpeg\" length=\"0\"/>"
        if a.image_url else ""
    )
    categories = ""
    # Tags loaded lazily — skip if not loaded to avoid N+1
    # Frontend and search engines rely on the article page for full metadata

    return textwrap.dedent(f"""\
        <item>
          <title>{_esc(a.title)}</title>
          <link>{article_url}</link>
          <guid isPermaLink="true">{article_url}</guid>
          <pubDate>{pub_date}</pubDate>
          <description>{summary}</description>
          <source url="{_SITE_URL}">{_esc(settings.app_name)}</source>{image_tag}
        </item>""")


def _brief_to_item(b: DailyBrief) -> str:
    # Build a UTC datetime from the date string
    try:
        dt = datetime.fromisoformat(f"{b.date}T06:00:00+00:00")
    except ValueError:
        dt = datetime.now(timezone.utc)
    pub_date = format_datetime(dt)
    brief_url = f"{_SITE_URL}/daily/{b.date}"

    return textwrap.dedent(f"""\
        <item>
          <title>{_esc(b.headline)}</title>
          <link>{brief_url}</link>
          <guid isPermaLink="true">{brief_url}</guid>
          <pubDate>{pub_date}</pubDate>
          <description>{_esc(b.summary[:500] if b.summary else "")}</description>
        </item>""")


def _esc(text: str) -> str:
    """Escape special XML characters."""
    return html.escape(str(text), quote=True)
