"""
Summarization prompt templates.

Output contract (JSON):
{
  "summary":          "2-3 sentence paragraph summarising the article.",
  "bullets":          ["Key point 1", "Key point 2", "Key point 3"],
  "meta_description": "SEO-ready sentence ≤160 chars."
}
"""
from __future__ import annotations

SUMMARIZE_SYSTEM = """\
You are an expert AI industry analyst. Your job is to produce concise,
accurate summaries of AI-related news articles for a professional audience
of researchers, engineers, and investors.

Guidelines:
- Summary: 2-3 sentences. Lead with the most important fact. Be specific.
- Bullets: exactly 3 bullet points. Each starts with a strong verb.
  Focus on: what happened, why it matters, what changes.
- Meta description: one sentence, ≤160 characters, SEO-optimised.
  Include key entities (company/model names).

Avoid:
- Marketing language ("revolutionary", "game-changing")
- Speculation beyond what the article states
- Repeating the title verbatim

Respond with a JSON object only. No markdown fences, no extra text.
"""


def build_summarize_prompt(
    title: str,
    content: str,
    source: str = "",
) -> str:
    source_line = f"Source: {source}\n" if source else ""
    return f"""\
{source_line}Title: {title}

Article content:
{content}

Respond with this exact JSON structure:
{{
  "summary": "<2-3 sentence summary>",
  "bullets": ["<bullet 1>", "<bullet 2>", "<bullet 3>"],
  "meta_description": "<≤160 char SEO description>"
}}"""
