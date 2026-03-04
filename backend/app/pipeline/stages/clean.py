"""
Stage: clean

Normalises text fields:
  - strips HTML remnants, ads, nav boilerplate
  - normalises whitespace and Unicode
  - enforces title/content length limits
  - detects language
  - generates url_hash and slug
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import timezone, datetime
from typing import Optional
from urllib.parse import urlparse

import structlog

from app.pipeline.base import PipelineContext, PipelineStageBase

logger = structlog.get_logger(__name__)

# Boilerplate patterns to strip from content
_BOILERPLATE_PATTERNS: list[re.Pattern] = [
    re.compile(r"Subscribe to.*?newsletter", re.I | re.S),
    re.compile(r"Sign up for.*?updates", re.I | re.S),
    re.compile(r"©\s*\d{4}.*", re.I),
    re.compile(r"All rights reserved.*", re.I),
    re.compile(r"Read more:.*", re.I),
    re.compile(r"Related articles?:.*", re.I),
    re.compile(r"\[.*?advertisement.*?\]", re.I),
]

_MAX_TITLE_LEN = 300
_MAX_CONTENT_LEN = 50_000   # ~10k words; trim beyond this
_MAX_SLUG_LEN = 200


class CleanStage(PipelineStageBase):
    name = "clean"

    async def process(self, ctx: PipelineContext) -> PipelineContext:
        cleaned: list[dict] = []
        skipped = 0

        for article in ctx.articles:
            try:
                article = _clean_article(article)
                if article:
                    cleaned.append(article)
                else:
                    skipped += 1
            except Exception as exc:
                ctx.add_error(self.name, f"url={article.get('url', '?')}: {exc}")
                skipped += 1

        ctx.articles = cleaned
        ctx.set_stage_stat(self.name, "cleaned", len(cleaned))
        ctx.set_stage_stat(self.name, "skipped", skipped)
        return ctx


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clean_article(article: dict) -> Optional[dict]:
    title = _clean_text(article.get("title", ""))
    if not title:
        return None

    title = title[:_MAX_TITLE_LEN]
    article["title"] = title

    # Clean content
    content = article.get("clean_content") or article.get("raw_content", "")
    content = _clean_text(content)
    content = _strip_boilerplate(content)
    content = content[:_MAX_CONTENT_LEN]
    article["clean_content"] = content
    article["word_count"] = len(content.split()) if content else 0

    # URL hash (dedup key)
    url = _normalise_url(article.get("url", ""))
    if not url:
        return None
    article["url"] = url
    article["url_hash"] = hashlib.sha256(url.encode()).hexdigest()

    # Slug
    article["slug"] = _make_slug(title, article.get("published_at"))

    # Normalise published_at to ISO string
    pub = article.get("published_at")
    if isinstance(pub, datetime):
        article["published_at"] = pub.isoformat()
    elif pub is None:
        article["published_at"] = datetime.now(timezone.utc).isoformat()

    return article


def _clean_text(text: str) -> str:
    if not text:
        return ""
    # Normalise unicode
    text = unicodedata.normalize("NFKC", text)
    # Remove HTML tags (fallback in case readability missed some)
    text = re.sub(r"<[^>]+>", " ", text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _strip_boilerplate(text: str) -> str:
    for pat in _BOILERPLATE_PATTERNS:
        text = pat.sub("", text)
    return text.strip()


def _normalise_url(url: str) -> str:
    """Remove tracking params, normalise scheme."""
    try:
        parsed = urlparse(url.strip())
        # Remove common UTM / tracking params
        from urllib.parse import parse_qs, urlencode
        params = parse_qs(parsed.query)
        clean_params = {
            k: v for k, v in params.items()
            if not k.lower().startswith(("utm_", "ref", "source", "mc_"))
        }
        clean_query = urlencode(clean_params, doseq=True)
        return parsed._replace(
            scheme=parsed.scheme.lower(),
            netloc=parsed.netloc.lower(),
            query=clean_query,
            fragment="",
        ).geturl()
    except Exception:
        return url


def _make_slug(title: str, published_at: Optional[str]) -> str:
    """Generate a URL-safe slug from title + date suffix."""
    # Lowercase, replace non-alphanumeric with dash
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower())
    slug = slug.strip("-")[:_MAX_SLUG_LEN - 11]  # leave room for date suffix

    # Date suffix ensures uniqueness across days
    date_suffix = ""
    if published_at:
        try:
            date_suffix = "-" + published_at[:10]  # YYYY-MM-DD
        except Exception:
            pass

    return f"{slug}{date_suffix}"
