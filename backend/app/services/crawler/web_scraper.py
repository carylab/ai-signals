"""
Web Scraper — fallback for sources without RSS feeds.

Strategy per source type:
  - Generic:    fetch homepage / section page, extract article links,
                fetch each article link
  - Known site: per-site CSS selector rules defined in SITE_CONFIGS

The scraper does NOT render JavaScript. Sites that require JS
(e.g. React SPAs) are handled by the playwright-based renderer
in V2. For MVP we skip JS-only sources or use their RSS if available.
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urljoin, urlparse

import structlog
from lxml import html as lxml_html

from app.services.crawler import RawArticle
from app.services.crawler.http_client import fetch_url

logger = structlog.get_logger(__name__)

_MAX_ARTICLES_PER_SOURCE = 20


@dataclass
class SiteConfig:
    """CSS/XPath selectors for a specific site."""
    article_links: str          # CSS selector for article <a> tags on listing page
    title: str = "h1"
    content: str = "article"
    author: str = ""
    date: str = ""
    # Optional: override the listing page URL (default = source.url)
    listing_url: Optional[str] = None
    # Selector relative to the listing page to extract dates from feed rows
    listing_date: str = ""
    # Max articles to scrape per run (override global limit)
    max_articles: int = _MAX_ARTICLES_PER_SOURCE


# Per-site extraction configs.
# Key = domain (without www.)
SITE_CONFIGS: dict[str, SiteConfig] = {
    "mistral.ai": SiteConfig(
        article_links="a[href*='/news/']",
        title="h1",
        content="article, .prose, main",
        date="time",
    ),
    "theinformation.com": SiteConfig(
        article_links="a[href*='/articles/']",
        title="h1.article-title",
        content=".article-body",
        author=".author-name",
        date="time[datetime]",
    ),
    "scale.com": SiteConfig(
        article_links="a[href*='/blog/']",
        title="h1",
        content=".blog-content, .post-content",
        date="time",
        max_articles=10,
    ),
}


class WebScraper:
    """Scrape articles from sources that have no RSS feed."""

    async def fetch(self, source) -> list[dict]:
        """
        Args:
            source: NewsSource ORM object

        Returns:
            list of raw article dicts
        """
        domain = _extract_domain(source.url)
        config = SITE_CONFIGS.get(domain) or _default_config()
        listing_url = config.listing_url or source.url

        log = logger.bind(source=source.slug, url=listing_url)

        try:
            article_urls = await self._get_article_urls(listing_url, config)
        except Exception as exc:
            log.error("scraper_listing_error", error=str(exc))
            raise

        log.info("scraper_links_found", count=len(article_urls))

        # Fetch each article page concurrently (bounded)
        sem = asyncio.Semaphore(5)
        tasks = [
            self._scrape_article(url, source, config, sem)
            for url in article_urls[: config.max_articles]
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        articles: list[dict] = []
        for result in results:
            if isinstance(result, Exception):
                log.warning("scraper_article_error", error=str(result))
            elif result is not None:
                articles.append(result.to_dict())

        log.info("scraper_done", fetched=len(articles))
        return articles

    async def _get_article_urls(
        self, listing_url: str, config: SiteConfig
    ) -> list[str]:
        """Fetch the listing/index page and extract article links."""
        response = await fetch_url(listing_url)
        tree = lxml_html.fromstring(response.text)
        tree.make_links_absolute(listing_url)

        # Try CSS selector
        links: list[str] = []
        try:
            elements = tree.cssselect(config.article_links)
            for el in elements:
                href = el.get("href", "")
                if href and href.startswith("http"):
                    links.append(href)
        except Exception:
            # Fallback: collect all <a> links that look like article URLs
            links = _heuristic_article_links(tree, listing_url)

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique: list[str] = []
        for link in links:
            clean = link.split("?")[0].split("#")[0]
            if clean not in seen:
                seen.add(clean)
                unique.append(clean)

        return unique

    async def _scrape_article(
        self,
        url: str,
        source,
        config: SiteConfig,
        sem: asyncio.Semaphore,
    ) -> Optional[RawArticle]:
        async with sem:
            try:
                response = await fetch_url(url)
            except Exception as exc:
                logger.debug("scraper_fetch_fail", url=url, error=str(exc))
                return None

            tree = lxml_html.fromstring(response.text)
            tree.make_links_absolute(url)

            title = _extract_text(tree, config.title) or _og_title(tree)
            if not title:
                return None

            content_html = _extract_html(tree, config.content)
            author = _extract_text(tree, config.author) if config.author else ""
            published_at = _extract_date(tree, config.date)
            image_url = _og_image(tree)

            return RawArticle(
                url=url,
                title=title,
                source_id=source.id,
                source_slug=source.slug,
                source_priority=source.priority,
                published_at=published_at,
                raw_content=content_html,
                author=author,
                image_url=image_url,
            )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _default_config() -> SiteConfig:
    return SiteConfig(
        article_links="a[href*='/blog/'], a[href*='/news/'], a[href*='/article/'], a[href*='/post/']",
        title="h1",
        content="article, .post-content, .article-body, .entry-content, main",
        date="time[datetime], .published, .date",
    )


def _extract_domain(url: str) -> str:
    netloc = urlparse(url).netloc.lower()
    return netloc.lstrip("www.")


def _extract_text(tree: lxml_html.HtmlElement, selector: str) -> str:
    if not selector:
        return ""
    try:
        elements = tree.cssselect(selector)
        if elements:
            return " ".join(elements[0].text_content().split()).strip()
    except Exception:
        pass
    return ""


def _extract_html(tree: lxml_html.HtmlElement, selector: str) -> str:
    if not selector:
        return lxml_html.tostring(tree, encoding="unicode")
    for sel in selector.split(","):
        sel = sel.strip()
        try:
            elements = tree.cssselect(sel)
            if elements:
                return lxml_html.tostring(elements[0], encoding="unicode")
        except Exception:
            continue
    return lxml_html.tostring(tree, encoding="unicode")


def _extract_date(tree: lxml_html.HtmlElement, selector: str) -> Optional[datetime]:
    if not selector:
        return _meta_date(tree)

    for sel in selector.split(","):
        sel = sel.strip()
        try:
            elements = tree.cssselect(sel)
            if not elements:
                continue
            el = elements[0]
            # Try datetime attribute first (ISO 8601)
            dt_attr = el.get("datetime") or el.get("data-datetime")
            if dt_attr:
                return _parse_iso(dt_attr)
            # Try text content
            text = el.text_content().strip()
            if text:
                return _parse_iso(text)
        except Exception:
            continue

    return _meta_date(tree)


def _parse_iso(value: str) -> Optional[datetime]:
    """Parse ISO-8601 or common date formats."""
    import email.utils

    value = value.strip()
    # Try ISO first
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(value[:25], fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue

    # RFC 2822 (common in HTML meta tags)
    try:
        return email.utils.parsedate_to_datetime(value).astimezone(timezone.utc)
    except Exception:
        pass

    return None


def _meta_date(tree: lxml_html.HtmlElement) -> Optional[datetime]:
    """Extract date from Open Graph / article meta tags."""
    for attr in (
        "article:published_time",
        "og:updated_time",
        "datePublished",
        "pubdate",
    ):
        try:
            els = tree.cssselect(f'meta[property="{attr}"], meta[name="{attr}"]')
            for el in els:
                val = el.get("content", "")
                if val:
                    dt = _parse_iso(val)
                    if dt:
                        return dt
        except Exception:
            continue
    return None


def _og_title(tree: lxml_html.HtmlElement) -> str:
    try:
        els = tree.cssselect('meta[property="og:title"]')
        if els:
            return els[0].get("content", "").strip()
    except Exception:
        pass
    return ""


def _og_image(tree: lxml_html.HtmlElement) -> Optional[str]:
    try:
        els = tree.cssselect('meta[property="og:image"]')
        if els:
            src = els[0].get("content", "").strip()
            if src.startswith("http"):
                return src
    except Exception:
        pass
    return None


def _heuristic_article_links(
    tree: lxml_html.HtmlElement, base_url: str
) -> list[str]:
    """
    Collect links that look like article URLs when no CSS selector matches.
    Heuristic: path has at least 2 segments, doesn't look like nav/footer.
    """
    links: list[str] = []
    parsed_base = urlparse(base_url)

    for el in tree.cssselect("a[href]"):
        href: str = el.get("href", "")
        if not href.startswith("http"):
            href = urljoin(base_url, href)

        parsed = urlparse(href)
        if parsed.netloc != parsed_base.netloc:
            continue

        path = parsed.path.rstrip("/")
        segments = [s for s in path.split("/") if s]

        # Skip short paths (home, /about, /contact)
        if len(segments) < 2:
            continue

        # Skip obvious non-article paths
        skip_words = {"tag", "category", "author", "page", "feed", "rss",
                      "search", "login", "signup", "subscribe", "cdn-cgi"}
        if any(seg.lower() in skip_words for seg in segments):
            continue

        links.append(href)

    return links
