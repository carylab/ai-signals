"""
Daily Brief prompt templates.

Output contract (JSON):
{
  "headline":    "Single punchy headline for the day's AI news (≤120 chars)",
  "summary":     "3-5 paragraph narrative of the day's most important AI events",
  "key_themes":  ["Theme 1", "Theme 2", "Theme 3"]
}
"""
from __future__ import annotations

BRIEF_SYSTEM = """\
You are the lead analyst at an AI industry intelligence newsletter, writing
for a senior audience: investors, researchers, engineers, and founders.

Your daily brief should:
- Open with the single most consequential story of the day
- Connect related stories into coherent narratives
- Note emerging patterns or trend inflections
- Flag anything that represents a genuine industry shift
- End with a "Watch" — one forward-looking observation

Tone: Direct, analytical, authoritative. No hype, no filler.
Length: 3-5 substantive paragraphs (~300-500 words total).

Respond with a JSON object only. No markdown fences, no extra text.
"""


def build_brief_prompt(
    date: str,
    articles: list[dict],
    trending_tags: list[str],
) -> str:
    """
    Args:
        date:          Target date string "YYYY-MM-DD"
        articles:      List of dicts with keys: title, summary, score
        trending_tags: List of trending tag names for context
    """
    articles_text = _format_articles(articles)
    tags_text = ", ".join(trending_tags) if trending_tags else "none"

    return f"""\
Date: {date}

Today's trending topics: {tags_text}

Top stories (ranked by importance):
{articles_text}

Write a daily AI intelligence brief for {date}.

Respond with this exact JSON structure:
{{
  "headline":   "<punchy single headline ≤120 chars>",
  "summary":    "<3-5 paragraph narrative>",
  "key_themes": ["<theme 1>", "<theme 2>", "<theme 3>"]
}}"""


def _format_articles(articles: list[dict]) -> str:
    lines: list[str] = []
    for i, a in enumerate(articles, 1):
        title = a.get("title", "")
        summary = a.get("summary", "")
        score = a.get("score", 0)
        lines.append(f"{i}. [{score:.2f}] {title}")
        if summary:
            # Indent summary under the title
            lines.append(f"   {summary[:200]}")
    return "\n".join(lines)
