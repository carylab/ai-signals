"""
seed_sources.py — populate the news_sources table with 30+ curated AI sources.

Usage:
    python scripts/seed_sources.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.config import settings
from app.core.database import init_db, get_session, create_all_tables
from app.models.source import NewsSource, SourceType, SourceCategory

SOURCES: list[dict] = [
    # ── Tier-1 AI Media ──────────────────────────────────────────────────────
    {
        "name": "TechCrunch AI",
        "slug": "techcrunch-ai",
        "url": "https://techcrunch.com/category/artificial-intelligence/",
        "feed_url": "https://techcrunch.com/category/artificial-intelligence/feed/",
        "source_type": SourceType.RSS,
        "category": SourceCategory.MEDIA,
        "priority": 1,
    },
    {
        "name": "MIT Technology Review",
        "slug": "mit-tech-review",
        "url": "https://www.technologyreview.com",
        "feed_url": "https://www.technologyreview.com/feed/",
        "source_type": SourceType.RSS,
        "category": SourceCategory.MEDIA,
        "priority": 1,
    },
    {
        "name": "Wired AI",
        "slug": "wired-ai",
        "url": "https://www.wired.com/tag/artificial-intelligence/",
        "feed_url": "https://www.wired.com/feed/tag/ai/latest/rss",
        "source_type": SourceType.RSS,
        "category": SourceCategory.MEDIA,
        "priority": 1,
    },
    {
        "name": "VentureBeat AI",
        "slug": "venturebeat-ai",
        "url": "https://venturebeat.com/category/ai/",
        "feed_url": "https://venturebeat.com/category/ai/feed/",
        "source_type": SourceType.RSS,
        "category": SourceCategory.MEDIA,
        "priority": 1,
    },
    {
        "name": "The Verge AI",
        "slug": "theverge-ai",
        "url": "https://www.theverge.com/ai-artificial-intelligence",
        "feed_url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
        "source_type": SourceType.RSS,
        "category": SourceCategory.MEDIA,
        "priority": 2,
    },
    {
        "name": "Ars Technica AI",
        "slug": "ars-technica-ai",
        "url": "https://arstechnica.com/ai/",
        "feed_url": "https://feeds.arstechnica.com/arstechnica/technology-lab",
        "source_type": SourceType.RSS,
        "category": SourceCategory.MEDIA,
        "priority": 2,
    },
    # ── AI-Specific Newsletters / Blogs ──────────────────────────────────────
    {
        "name": "The Batch (DeepLearning.AI)",
        "slug": "the-batch",
        "url": "https://www.deeplearning.ai/the-batch/",
        "feed_url": "https://www.deeplearning.ai/the-batch/feed/",
        "source_type": SourceType.RSS,
        "category": SourceCategory.RESEARCH,
        "priority": 1,
    },
    {
        "name": "Import AI (Jack Clark)",
        "slug": "import-ai",
        "url": "https://jack-clark.net",
        "feed_url": "https://jack-clark.net/feed/",
        "source_type": SourceType.RSS,
        "category": SourceCategory.RESEARCH,
        "priority": 1,
    },
    {
        "name": "AI Breakfast",
        "slug": "ai-breakfast",
        "url": "https://aibreakfast.beehiiv.com",
        "feed_url": "https://aibreakfast.beehiiv.com/feed",
        "source_type": SourceType.RSS,
        "category": SourceCategory.MEDIA,
        "priority": 2,
    },
    {
        "name": "The AI Edge",
        "slug": "the-ai-edge",
        "url": "https://theaiedge.io",
        "feed_url": "https://theaiedge.io/feed/",
        "source_type": SourceType.RSS,
        "category": SourceCategory.MEDIA,
        "priority": 3,
    },
    # ── Company Blogs ────────────────────────────────────────────────────────
    {
        "name": "OpenAI Blog",
        "slug": "openai-blog",
        "url": "https://openai.com/blog",
        "feed_url": "https://openai.com/blog/rss.xml",
        "source_type": SourceType.RSS,
        "category": SourceCategory.COMPANY,
        "priority": 1,
    },
    {
        "name": "Anthropic Blog",
        "slug": "anthropic-blog",
        "url": "https://www.anthropic.com/news",
        "feed_url": "https://www.anthropic.com/rss.xml",
        "source_type": SourceType.RSS,
        "category": SourceCategory.COMPANY,
        "priority": 1,
    },
    {
        "name": "Google DeepMind Blog",
        "slug": "deepmind-blog",
        "url": "https://deepmind.google/discover/blog/",
        "feed_url": "https://deepmind.google/blog/rss.xml",
        "source_type": SourceType.RSS,
        "category": SourceCategory.COMPANY,
        "priority": 1,
    },
    {
        "name": "Meta AI Blog",
        "slug": "meta-ai-blog",
        "url": "https://ai.meta.com/blog/",
        "feed_url": "https://ai.meta.com/blog/rss/",
        "source_type": SourceType.RSS,
        "category": SourceCategory.COMPANY,
        "priority": 1,
    },
    {
        "name": "Microsoft Research Blog",
        "slug": "microsoft-research",
        "url": "https://www.microsoft.com/en-us/research/blog/",
        "feed_url": "https://www.microsoft.com/en-us/research/feed/",
        "source_type": SourceType.RSS,
        "category": SourceCategory.COMPANY,
        "priority": 2,
    },
    {
        "name": "Hugging Face Blog",
        "slug": "huggingface-blog",
        "url": "https://huggingface.co/blog",
        "feed_url": "https://huggingface.co/blog/feed.xml",
        "source_type": SourceType.RSS,
        "category": SourceCategory.COMPANY,
        "priority": 1,
    },
    {
        "name": "Mistral AI Blog",
        "slug": "mistral-blog",
        "url": "https://mistral.ai/news/",
        "feed_url": None,
        "source_type": SourceType.SCRAPE,
        "category": SourceCategory.COMPANY,
        "priority": 2,
    },
    # ── Research ─────────────────────────────────────────────────────────────
    {
        "name": "ArXiv CS.AI",
        "slug": "arxiv-cs-ai",
        "url": "https://arxiv.org/list/cs.AI/recent",
        "feed_url": "https://rss.arxiv.org/rss/cs.AI",
        "source_type": SourceType.RSS,
        "category": SourceCategory.RESEARCH,
        "priority": 2,
    },
    {
        "name": "ArXiv CS.LG",
        "slug": "arxiv-cs-lg",
        "url": "https://arxiv.org/list/cs.LG/recent",
        "feed_url": "https://rss.arxiv.org/rss/cs.LG",
        "source_type": SourceType.RSS,
        "category": SourceCategory.RESEARCH,
        "priority": 2,
    },
    {
        "name": "Google AI Blog",
        "slug": "google-ai-blog",
        "url": "https://ai.googleblog.com",
        "feed_url": "http://feeds.feedburner.com/blogspot/gJZg",
        "source_type": SourceType.RSS,
        "category": SourceCategory.RESEARCH,
        "priority": 1,
    },
    # ── Community ────────────────────────────────────────────────────────────
    {
        "name": "Hacker News (AI)",
        "slug": "hacker-news-ai",
        "url": "https://news.ycombinator.com",
        "feed_url": "https://hnrss.org/newest?q=AI+LLM+machine+learning&points=50",
        "source_type": SourceType.RSS,
        "category": SourceCategory.COMMUNITY,
        "priority": 3,
    },
    {
        "name": "Reddit r/MachineLearning",
        "slug": "reddit-ml",
        "url": "https://www.reddit.com/r/MachineLearning/",
        "feed_url": "https://www.reddit.com/r/MachineLearning/.rss",
        "source_type": SourceType.RSS,
        "category": SourceCategory.COMMUNITY,
        "priority": 4,
    },
    {
        "name": "Reddit r/LocalLLaMA",
        "slug": "reddit-localllama",
        "url": "https://www.reddit.com/r/LocalLLaMA/",
        "feed_url": "https://www.reddit.com/r/LocalLLaMA/.rss",
        "source_type": SourceType.RSS,
        "category": SourceCategory.COMMUNITY,
        "priority": 3,
    },
    # ── Finance / Funding ────────────────────────────────────────────────────
    {
        "name": "TechCrunch Funding",
        "slug": "techcrunch-funding",
        "url": "https://techcrunch.com/category/venture/",
        "feed_url": "https://techcrunch.com/category/venture/feed/",
        "source_type": SourceType.RSS,
        "category": SourceCategory.FINANCE,
        "priority": 2,
    },
    {
        "name": "The Information AI",
        "slug": "the-information-ai",
        "url": "https://www.theinformation.com/technology/artificial-intelligence",
        "feed_url": None,
        "source_type": SourceType.SCRAPE,
        "category": SourceCategory.MEDIA,
        "priority": 1,
    },
]


async def seed() -> None:
    import os
    os.makedirs("./data/db", exist_ok=True)
    init_db(settings.database_url)
    await create_all_tables()

    async for session in get_session():
        for data in SOURCES:
            # Upsert by slug
            from sqlalchemy import select
            result = await session.execute(
                select(NewsSource).where(NewsSource.slug == data["slug"])
            )
            existing = result.scalar_one_or_none()
            if existing:
                for k, v in data.items():
                    setattr(existing, k, v)
                print(f"  updated: {data['slug']}")
            else:
                session.add(NewsSource(**data))
                print(f"  inserted: {data['slug']}")

    print(f"\nSeeded {len(SOURCES)} sources.")


if __name__ == "__main__":
    asyncio.run(seed())
