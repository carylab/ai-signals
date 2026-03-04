// Shared TypeScript types — mirrors backend Pydantic schemas

export interface Tag {
  slug: string
  name: string
  category: string
  trend_score: number
  news_count_7d: number
  news_count_30d: number
  description?: string
}

export interface Company {
  slug: string
  name: string
  description?: string
  website?: string
  trend_score: number
  news_count_7d: number
  is_verified: boolean
}

export interface AIModel {
  slug: string
  name: string
  model_type?: string
  is_open_source: boolean
  trend_score: number
  news_count_7d: number
}

export interface ArticleListItem {
  id: number
  slug: string
  title: string
  url: string
  published_at: string | null
  summary: string | null
  meta_description: string | null
  image_url: string | null
  author: string | null
  importance_score: number
  freshness_score: number
  trend_score: number
  discussion_score: number
  final_score: number
  is_cluster_representative: boolean
  cluster_id: number | null
  word_count: number | null
  tags: Tag[]
  companies: Company[]
}

export interface ArticleDetail extends ArticleListItem {
  clean_content: string | null
  summary_bullets: string[]
  ai_models: AIModel[]
  llm_model_used: string | null
  pipeline_stage: string
}

export interface BriefTopStory {
  id: number
  slug: string
  title: string
  summary: string | null
  final_score: number
  published_at: string | null
  image_url?: string | null
}

export interface DailyBrief {
  date: string
  headline: string
  summary: string
  key_themes: string[]
  is_published: boolean
  llm_model_used: string | null
  total_articles_processed: number
  total_articles_published: number
  avg_importance_score: number
  top_stories: BriefTopStory[]
  trending_tags: Tag[]
}

export interface TrendSnapshot {
  date: string
  entity_type: string
  slug: string
  name: string
  trend_score: number
  velocity: number
  count_1d: number
  count_7d: number
  count_30d: number
}

export interface SearchResult {
  articles: ArticleListItem[]
  total: number
  query: string
  took_ms: number
}

export interface PaginatedResponse<T> {
  data: T[]
  total: number
  page: number
  page_size: number
  has_next: boolean
  has_prev: boolean
}

export interface PlatformStats {
  total_articles: number
  published_articles: number
  total_sources: number
  active_sources: number
  total_tags: number
  total_companies: number
  total_briefs: number
  last_pipeline_run: string | null
  last_pipeline_status: string | null
  articles_today: number
  avg_daily_articles_7d: number
}
