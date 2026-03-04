"""
Application configuration.

All values are read from environment variables or a .env file.
Pydantic-settings validates types at startup — the app will refuse
to start if required values are missing or malformed.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal, Optional

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────────────────────
    app_name: str = "AI Signals"
    app_env: Literal["development", "production", "test"] = "development"
    debug: bool = False
    secret_key: str = Field(default="change-me-in-production", min_length=16)
    allowed_origins: str = "http://localhost:3000,http://localhost:3001"

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./data/db/ai_signals.db"
    # PostgreSQL example:
    #   postgresql+asyncpg://user:password@localhost:5432/ai_signals

    # ── LLM ──────────────────────────────────────────────────────────────────
    llm_provider: Literal["openai", "anthropic", "deepseek", "openrouter"] = "openai"
    llm_model: str = "gpt-4o-mini"

    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    deepseek_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None

    llm_max_retries: int = Field(default=3, ge=1, le=10)
    llm_timeout_s: int = Field(default=60, ge=10, le=300)
    llm_temperature: float = Field(default=0.3, ge=0.0, le=2.0)

    # ── Pipeline ─────────────────────────────────────────────────────────────
    pipeline_max_articles_per_run: int = Field(default=500, ge=10)
    pipeline_min_publish_score: float = Field(default=0.25, ge=0.0, le=1.0)
    pipeline_similarity_threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    pipeline_cron: str = "0 6 * * *"   # 06:00 UTC daily
    pipeline_enabled: bool = True       # set False to pause scheduled runs

    # ── Crawler ───────────────────────────────────────────────────────────────
    crawler_request_timeout_s: int = Field(default=30, ge=5, le=120)
    crawler_max_concurrent: int = Field(default=10, ge=1, le=50)
    crawler_user_agent: str = "AISignals/1.0 (+https://aisignals.io/bot)"

    # ── Export / Frontend ────────────────────────────────────────────────────
    export_dir: str = "./data/exports"

    # ── Logging ───────────────────────────────────────────────────────────────
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_format: Literal["json", "console"] = "console"
    # Production should use "json" for log aggregation pipelines

    # ── API ───────────────────────────────────────────────────────────────────
    api_default_page_size: int = Field(default=20, ge=1, le=100)
    api_max_page_size: int = Field(default=100, ge=1, le=500)

    # ── Validators ────────────────────────────────────────────────────────────
    @model_validator(mode="after")
    def check_llm_key_present(self) -> "Settings":
        key_map = {
            "openai": self.openai_api_key,
            "anthropic": self.anthropic_api_key,
            "deepseek": self.deepseek_api_key,
            "openrouter": self.openrouter_api_key,
        }
        key = key_map.get(self.llm_provider)
        if not key and self.app_env != "test":
            raise ValueError(
                f"llm_provider={self.llm_provider!r} but the corresponding "
                f"API key is not set."
            )
        return self

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def active_llm_key(self) -> Optional[str]:
        return {
            "openai": self.openai_api_key,
            "anthropic": self.anthropic_api_key,
            "deepseek": self.deepseek_api_key,
            "openrouter": self.openrouter_api_key,
        }.get(self.llm_provider)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return a cached Settings singleton.
    Import this instead of instantiating Settings directly.

        from app.config import get_settings
        settings = get_settings()
    """
    return Settings()


# Module-level convenience alias used throughout the codebase
settings: Settings = get_settings()
