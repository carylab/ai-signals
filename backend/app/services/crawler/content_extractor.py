"""
Content Extractor — converts raw HTML into clean article text.

Uses readability-lxml (Mozilla Readability port) to identify
and extract the main article body, stripping navigation, ads,
footers, and other boilerplate.

Also extracts:
  - word_count
  - author (from meta tags)
  - image_url (og:image)
  - language (from <html lang> or heuristic)
"""
from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urlparse

import structlog
from lxml import html as lxml_html
from readability import Document  # readability-lxml

from app.services.crawler.http_client import fetch_url

logger = structlog.get_logger(__name__)

# Minimum word count to consider extraction successful
_MIN_WORDS = 50


class ContentExtractor:
    """
    Extracts clean article content from raw HTML.

    Usage:
        extractor = ContentExtractor()
        html = await extractor.fetch_html(url)
        result = extractor.extract(html, url)
    """

    async def fetch_html(self, url: str) -> str:
        """Fetch raw HTML for a URL. Used by ExtractStage when content is missing."""
        response = await fetch_url(url)
        return response.text

    def extract(self, raw_html: str, url: str) -> dict:
        """
        Extract structured content from raw HTML.

        Returns a dict with keys:
            clean_content  — plain text article body
            title          — article title (may override feed title)
            author         — author name(s)
            image_url      — representative image
            word_count     — word count of clean_content
            language       — ISO 639-1 code e.g. "en"
        """
        if not raw_html or len(raw_html.strip()) < 100:
            return _empty_result()

        try:
            return self._extract_with_readability(raw_html, url)
        except Exception as exc:
            logger.warning(
                "content_extract_error",
                url=url,
                error=str(exc),
            )
            # Fallback: basic text extraction
            return self._extract_fallback(raw_html, url)

    # ------------------------------------------------------------------
    # Primary: readability-lxml
    # ------------------------------------------------------------------

    def _extract_with_readability(self, raw_html: str, url: str) -> dict:
        doc = Document(raw_html, url=url)

        # readability gives us clean HTML; convert to plain text
        clean_html = doc.summary(html_partial=True)
        clean_text = _html_to_text(clean_html)

        if len(clean_text.split()) < _MIN_WORDS:
            # Readability found very little content; try fallback
            return self._extract_fallback(raw_html, url)

        # Also parse the original tree for metadata
        tree = _safe_parse(raw_html, url)

        return {
            "clean_content": clean_text,
            "title": _clean_title(doc.title()) or _og_meta(tree, "og:title"),
            "author": _extract_author(tree),
            "image_url": _og_meta(tree, "og:image"),
            "word_count": len(clean_text.split()),
            "language": _detect_language(tree, clean_text),
        }

    # ------------------------------------------------------------------
    # Fallback: naive lxml text extraction
    # ------------------------------------------------------------------

    def _extract_fallback(self, raw_html: str, url: str) -> dict:
        tree = _safe_parse(raw_html, url)
        if tree is None:
            return _empty_result()

        # Remove noise elements before extracting text
        _remove_elements(tree, [
            "script", "style", "nav", "header", "footer",
            "aside", "form", ".ad", ".ads", ".advertisement",
            "#comments", ".sidebar",
        ])

        # Try common article containers
        text = ""
        for selector in ("article", "main", ".post-content",
                         ".article-body", ".entry-content", "body"):
            try:
                els = tree.cssselect(selector)
                if els:
                    raw_text = els[0].text_content()
                    text = _normalise_whitespace(raw_text)
                    if len(text.split()) >= _MIN_WORDS:
                        break
            except Exception:
                continue

        return {
            "clean_content": text,
            "title": _og_meta(tree, "og:title") or "",
            "author": _extract_author(tree),
            "image_url": _og_meta(tree, "og:image"),
            "word_count": len(text.split()),
            "language": _detect_language(tree, text),
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _empty_result() -> dict:
    return {
        "clean_content": "",
        "title": "",
        "author": "",
        "image_url": None,
        "word_count": 0,
        "language": "en",
    }


def _safe_parse(
    raw_html: str, url: str
) -> Optional[lxml_html.HtmlElement]:
    try:
        tree = lxml_html.fromstring(raw_html)
        tree.make_links_absolute(url)
        return tree
    except Exception:
        return None


def _html_to_text(html_fragment: str) -> str:
    """Convert HTML to plain text, preserving paragraph breaks."""
    if not html_fragment:
        return ""
    try:
        tree = lxml_html.fromstring(html_fragment)
        # Insert newlines at block elements
        for tag in tree.iter("p", "br", "div", "li", "h1", "h2", "h3", "h4"):
            if tag.tail:
                tag.tail = "\n" + tag.tail
            else:
                tag.tail = "\n"
        text = tree.text_content()
        return _normalise_whitespace(text)
    except Exception:
        # Strip tags with regex as last resort
        text = re.sub(r"<[^>]+>", " ", html_fragment)
        return _normalise_whitespace(text)


def _normalise_whitespace(text: str) -> str:
    """Collapse runs of whitespace while preserving paragraph breaks."""
    # Preserve double newlines (paragraph breaks)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Collapse horizontal whitespace
    lines = [" ".join(line.split()) for line in text.splitlines()]
    return "\n".join(line for line in lines if line).strip()


def _clean_title(title: str) -> str:
    if not title:
        return ""
    # Remove common site-name suffixes:  "Article Title | Site Name"
    title = re.sub(r"\s*[\|–\-—]\s*.{3,40}$", "", title)
    return " ".join(title.split()).strip()


def _extract_author(tree: Optional[lxml_html.HtmlElement]) -> str:
    if tree is None:
        return ""

    # Try structured meta first
    for selector in (
        'meta[name="author"]',
        'meta[property="article:author"]',
        '[rel="author"]',
        ".author-name",
        ".byline",
        '[itemprop="author"]',
    ):
        try:
            els = tree.cssselect(selector)
            if els:
                value = els[0].get("content") or els[0].text_content()
                value = " ".join(value.split()).strip()
                if value and len(value) < 100:
                    return value
        except Exception:
            continue

    return ""


def _og_meta(tree: Optional[lxml_html.HtmlElement], prop: str) -> str:
    if tree is None:
        return ""
    try:
        els = tree.cssselect(f'meta[property="{prop}"], meta[name="{prop}"]')
        if els:
            return els[0].get("content", "").strip()
    except Exception:
        pass
    return ""


def _detect_language(
    tree: Optional[lxml_html.HtmlElement], text: str
) -> str:
    """
    Detect content language.
    Priority: html[lang] > meta[http-equiv=Content-Language] > heuristic
    """
    if tree is not None:
        try:
            root = tree if tree.tag == "html" else tree.find(".//html")
            if root is not None:
                lang = root.get("lang", "")
                if lang:
                    return lang[:2].lower()
        except Exception:
            pass

        try:
            els = tree.cssselect('meta[http-equiv="Content-Language"]')
            if els:
                lang = els[0].get("content", "")[:2].lower()
                if lang:
                    return lang
        except Exception:
            pass

    # Very rough heuristic: non-ASCII heavy content = non-English
    if text:
        non_ascii = sum(1 for c in text if ord(c) > 127)
        if non_ascii / max(len(text), 1) > 0.15:
            return "unknown"

    return "en"


def _remove_elements(
    tree: lxml_html.HtmlElement, selectors: list[str]
) -> None:
    """Remove matching elements from tree in-place."""
    for selector in selectors:
        try:
            for el in tree.cssselect(selector):
                parent = el.getparent()
                if parent is not None:
                    parent.remove(el)
        except Exception:
            continue
