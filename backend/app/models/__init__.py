"""
Import all ORM models here so Alembic autogenerate and
create_all_tables() can discover them via Base.metadata.
"""
from app.models.source import NewsSource, SourceType, SourceCategory
from app.models.tag import Tag
from app.models.company import Company, AIModel
from app.models.news import NewsArticle, PipelineStage, article_tags, article_companies, article_models
from app.models.brief import DailyBrief
from app.models.pipeline_run import PipelineRun, RunStatus
from app.models.trend_snapshot import TrendSnapshot, EntityType

__all__ = [
    "NewsSource",
    "SourceType",
    "SourceCategory",
    "Tag",
    "Company",
    "AIModel",
    "NewsArticle",
    "PipelineStage",
    "article_tags",
    "article_companies",
    "article_models",
    "DailyBrief",
    "PipelineRun",
    "RunStatus",
    "TrendSnapshot",
    "EntityType",
]
