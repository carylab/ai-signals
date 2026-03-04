"""
Tests for the content extractor.
No network calls — all inputs are inline HTML strings.
"""
from __future__ import annotations

import pytest

from app.services.crawler.content_extractor import (
    ContentExtractor,
    _clean_title,
    _detect_language,
    _html_to_text,
    _normalise_whitespace,
)

SAMPLE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta property="og:title" content="OpenAI launches GPT-5">
  <meta property="og:image" content="https://example.com/img.jpg">
  <meta name="author" content="Jane Smith">
  <title>OpenAI launches GPT-5 | TechCrunch</title>
</head>
<body>
  <header><nav>Home | About | Contact</nav></header>
  <article>
    <h1>OpenAI launches GPT-5</h1>
    <p class="byline">By Jane Smith</p>
    <p>OpenAI today announced the release of GPT-5, its most capable
    language model to date. The new model demonstrates significant
    improvements in reasoning, coding, and multimodal understanding.</p>
    <p>The release comes after months of safety testing and follows
    intense competition from Anthropic and Google DeepMind.</p>
    <p>GPT-5 is available via the OpenAI API starting today, with
    ChatGPT integration rolling out over the next few weeks.</p>
  </article>
  <footer>© 2026 TechCrunch</footer>
</body>
</html>
"""

MINIMAL_HTML = "<html><body><p>Short.</p></body></html>"


@pytest.fixture
def extractor() -> ContentExtractor:
    return ContentExtractor()


class TestExtract:
    def test_extracts_content(self, extractor: ContentExtractor) -> None:
        result = extractor.extract(SAMPLE_HTML, "https://techcrunch.com/article")
        assert result["clean_content"]
        assert "GPT-5" in result["clean_content"]
        assert result["word_count"] > 20

    def test_extracts_author(self, extractor: ContentExtractor) -> None:
        result = extractor.extract(SAMPLE_HTML, "https://techcrunch.com/article")
        assert result["author"] == "Jane Smith"

    def test_extracts_image(self, extractor: ContentExtractor) -> None:
        result = extractor.extract(SAMPLE_HTML, "https://techcrunch.com/article")
        assert result["image_url"] == "https://example.com/img.jpg"

    def test_detects_english(self, extractor: ContentExtractor) -> None:
        result = extractor.extract(SAMPLE_HTML, "https://techcrunch.com/article")
        assert result["language"] == "en"

    def test_empty_html_returns_defaults(self, extractor: ContentExtractor) -> None:
        result = extractor.extract("", "https://example.com")
        assert result["clean_content"] == ""
        assert result["word_count"] == 0

    def test_minimal_html_falls_back(self, extractor: ContentExtractor) -> None:
        result = extractor.extract(MINIMAL_HTML, "https://example.com")
        # Should not raise; may return empty if below _MIN_WORDS threshold
        assert isinstance(result["clean_content"], str)


class TestHelpers:
    def test_clean_title_strips_site_name(self) -> None:
        assert _clean_title("Article Title | TechCrunch") == "Article Title"
        assert _clean_title("Story — BBC News") == "Story"

    def test_clean_title_empty(self) -> None:
        assert _clean_title("") == ""

    def test_html_to_text(self) -> None:
        html = "<p>Hello <strong>world</strong>.</p><p>Second paragraph.</p>"
        text = _html_to_text(html)
        assert "Hello" in text
        assert "world" in text

    def test_normalise_whitespace(self) -> None:
        messy = "  hello   world  \n\n\n  foo  "
        clean = _normalise_whitespace(messy)
        assert "   " not in clean
        assert "\n\n\n" not in clean


class TestRSSFetcherHelpers:
    def test_parse_date_from_struct(self) -> None:
        from app.services.crawler.rss_fetcher import _parse_date

        class FakeEntry:
            published_parsed = (2026, 3, 4, 12, 0, 0, 0, 0, 0)
            updated_parsed = None
            created_parsed = None
            published = ""
            updated = ""
            created = ""

        result = _parse_date(FakeEntry())
        assert result is not None
        assert result.year == 2026
        assert result.month == 3

    def test_parse_date_missing_returns_none(self) -> None:
        from app.services.crawler.rss_fetcher import _parse_date

        class FakeEntry:
            published_parsed = None
            updated_parsed = None
            created_parsed = None
            published = ""
            updated = ""
            created = ""

        assert _parse_date(FakeEntry()) is None
