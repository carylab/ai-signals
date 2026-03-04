"""
Stage: tag

Extracts structured entities and assigns topic tags using LLM.
Also runs rule-based entity extraction for known companies/models
to reduce LLM calls and improve consistency.

Output per article:
  tags         — list[str], e.g. ["LLM", "Funding", "Open Source"]
  companies    — list[str], e.g. ["OpenAI", "Anthropic"]
  ai_models    — list[str], e.g. ["GPT-4o", "Claude 3"]
  entities     — dict with structured NER results
"""
from __future__ import annotations

import asyncio
import json

import structlog

from app.pipeline.base import PipelineContext, PipelineStageBase

logger = structlog.get_logger(__name__)

_CONCURRENCY = 5


class TagStage(PipelineStageBase):
    name = "tag"

    def __init__(self, llm_client) -> None:
        self._llm = llm_client

    async def process(self, ctx: PipelineContext) -> PipelineContext:
        # Only tag cluster representatives (others inherit)
        reps = [a for a in ctx.articles if a.get("is_cluster_representative", True)]
        non_reps = [a for a in ctx.articles if not a.get("is_cluster_representative", True)]

        # Step 1: rule-based extraction (free, instant)
        for article in ctx.articles:
            _apply_rule_based_tags(article)

        # Step 2: LLM tagging for reps only
        sem = asyncio.Semaphore(_CONCURRENCY)
        tasks = [self._tag_one(a, sem, ctx) for a in reps]
        tagged_reps = list(await asyncio.gather(*tasks))

        # Non-reps inherit from rep
        rep_by_cluster: dict[int, dict] = {
            a["cluster_id"]: a
            for a in tagged_reps
            if a.get("cluster_id") is not None
        }
        for a in non_reps:
            rep = rep_by_cluster.get(a.get("cluster_id"))
            if rep:
                a["tags"] = rep.get("tags", [])
                a["companies"] = rep.get("companies", [])
                a["ai_models"] = rep.get("ai_models", [])
                a["entities"] = rep.get("entities", {})

        ctx.articles = tagged_reps + non_reps
        ctx.set_stage_stat(self.name, "tagged", len(tagged_reps))
        return ctx

    async def _tag_one(
        self,
        article: dict,
        sem: asyncio.Semaphore,
        ctx: PipelineContext,
    ) -> dict:
        async with sem:
            title = article.get("title", "")
            summary = article.get("summary", "")
            content_hint = (article.get("clean_content") or "")[:1000]

            try:
                from app.services.llm.prompts.tagging import (
                    TAGGING_SYSTEM,
                    build_tagging_prompt,
                )
                response = await self._llm.complete_json(
                    system=TAGGING_SYSTEM,
                    user=build_tagging_prompt(
                        title=title,
                        summary=summary,
                        content=content_hint,
                    ),
                )

                # Merge LLM results with rule-based (union)
                llm_tags = response.get("tags", [])
                llm_companies = response.get("companies", [])
                llm_models = response.get("ai_models", [])

                article["tags"] = _unique(
                    article.get("tags", []) + llm_tags
                )
                article["companies"] = _unique(
                    article.get("companies", []) + llm_companies
                )
                article["ai_models"] = _unique(
                    article.get("ai_models", []) + llm_models
                )
                article["entities"] = response.get("entities", {})

            except Exception as exc:
                ctx.add_error(self.name, f"url={article.get('url', '?')}: {exc}")
                # Keep rule-based results; don't wipe them

            return article


# ---------------------------------------------------------------------------
# Rule-based tagging (zero LLM cost)
# ---------------------------------------------------------------------------

_KNOWN_COMPANIES = {
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "google deepmind": "Google DeepMind",
    "meta ai": "Meta AI",
    "microsoft": "Microsoft",
    "amazon": "Amazon",
    "apple": "Apple",
    "mistral": "Mistral AI",
    "hugging face": "Hugging Face",
    "cohere": "Cohere",
    "stability ai": "Stability AI",
    "inflection": "Inflection AI",
    "xai": "xAI",
    "perplexity": "Perplexity",
    "character.ai": "Character.AI",
    "midjourney": "Midjourney",
    "runway": "Runway",
}

_KNOWN_MODELS = {
    "gpt-4": "GPT-4",
    "gpt-5": "GPT-5",
    "gpt-4o": "GPT-4o",
    "claude 3": "Claude 3",
    "claude 4": "Claude 4",
    "gemini": "Gemini",
    "llama": "LLaMA",
    "mistral": "Mistral",
    "deepseek": "DeepSeek",
    "qwen": "Qwen",
    "phi-": "Phi",
    "grok": "Grok",
    "stable diffusion": "Stable Diffusion",
    "dall-e": "DALL-E",
    "sora": "Sora",
    "whisper": "Whisper",
}

_TAG_KEYWORDS: dict[str, list[str]] = {
    "LLM": ["language model", "llm", "large language", "gpt", "claude", "gemini", "llama"],
    "Agent": ["ai agent", "autonomous agent", "agentic", "multi-agent"],
    "Funding": ["funding", "raises", "series a", "series b", "million", "billion", "invest", "valuation"],
    "Open Source": ["open source", "open-source", "github", "hugging face", "apache", "mit license"],
    "Research": ["paper", "arxiv", "research", "benchmark", "dataset", "study"],
    "Policy": ["regulation", "policy", "law", "government", "eu ai act", "executive order", "ban"],
    "Infra": ["infrastructure", "gpu", "nvidia", "training", "inference", "cloud", "cluster"],
    "Startup": ["startup", "founded", "launch", "new company", "spin-off"],
    "Safety": ["safety", "alignment", "red team", "jailbreak", "risk", "harm"],
    "Multimodal": ["multimodal", "vision", "image", "video", "audio", "speech"],
    "RAG": ["rag", "retrieval", "vector", "embedding", "knowledge base"],
    "Fine-tuning": ["fine-tun", "finetun", "lora", "qlora", "sft", "rlhf"],
}


def _apply_rule_based_tags(article: dict) -> None:
    text = (
        (article.get("title") or "") + " " +
        (article.get("summary") or "") + " " +
        (article.get("clean_content") or "")[:500]
    ).lower()

    tags: list[str] = list(article.get("tags") or [])
    companies: list[str] = list(article.get("companies") or [])
    models: list[str] = list(article.get("ai_models") or [])

    for keyword, canonical in _KNOWN_COMPANIES.items():
        if keyword in text and canonical not in companies:
            companies.append(canonical)

    for keyword, canonical in _KNOWN_MODELS.items():
        if keyword in text and canonical not in models:
            models.append(canonical)

    for tag, keywords in _TAG_KEYWORDS.items():
        if tag not in tags and any(kw in text for kw in keywords):
            tags.append(tag)

    article["tags"] = tags
    article["companies"] = companies
    article["ai_models"] = models


def _unique(lst: list) -> list:
    seen: set = set()
    result = []
    for x in lst:
        key = x.lower() if isinstance(x, str) else x
        if key not in seen:
            seen.add(key)
            result.append(x)
    return result
