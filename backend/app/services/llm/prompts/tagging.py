"""
Tagging prompt templates.

Output contract (JSON):
{
  "tags":      ["LLM", "Funding", "Open Source"],
  "companies": ["OpenAI", "Anthropic"],
  "ai_models": ["GPT-4o", "Claude 3.5"],
  "entities":  {
    "people":        ["Sam Altman"],
    "technologies":  ["transformer", "RLHF"],
    "locations":     ["San Francisco"]
  }
}
"""
from __future__ import annotations

# Valid tag taxonomy — LLM must only use these
VALID_TAGS = [
    "LLM", "Agent", "Open Source", "Funding", "Startup", "Research",
    "Policy", "Infra", "Safety", "Multimodal", "RAG", "Fine-tuning",
    "Robotics", "Voice", "Vision", "Benchmark", "Dataset", "Tool",
    "Product Launch", "Acquisition", "Partnership",
]

TAGGING_SYSTEM = f"""\
You are an AI industry intelligence system that extracts structured
metadata from news articles.

Valid tags (use ONLY from this list):
{", ".join(VALID_TAGS)}

Rules:
1. tags:      1-5 tags from the valid list above. Choose the most specific.
2. companies: canonical company names mentioned (e.g. "OpenAI", not "open ai").
              Only include AI-related companies central to the story.
              Max 5.
3. ai_models: specific AI model names (e.g. "GPT-4o", "Claude 3.5 Sonnet",
              "Llama 3.1"). Only include if explicitly named. Max 5.
4. entities:  extract people, technologies, and locations.
              people: key individuals (name + role if mentioned). Max 3.
              technologies: specific technical terms. Max 5.
              locations: countries or cities relevant to the story. Max 3.

Respond with a JSON object only. No markdown, no extra text.
"""


def build_tagging_prompt(
    title: str,
    summary: str,
    content: str = "",
) -> str:
    content_section = f"\nContent excerpt:\n{content}" if content else ""
    return f"""\
Title: {title}

Summary: {summary}
{content_section}

Respond with this exact JSON structure:
{{
  "tags":      ["<tag1>", "<tag2>"],
  "companies": ["<company1>"],
  "ai_models": ["<model1>"],
  "entities": {{
    "people":       ["<person1>"],
    "technologies": ["<tech1>"],
    "locations":    ["<location1>"]
  }}
}}"""
