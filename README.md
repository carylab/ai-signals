# AI Signals

Automated AI industry intelligence platform. Collects global AI news daily, processes it through a multi-stage LLM pipeline, scores and ranks articles, detects trends, and publishes a website with a daily briefing.

## What it does

- **Crawls** 25+ AI news sources via RSS and web scraping every day at 06:00 UTC
- **Deduplicates** articles using URL hashing and SimHash near-duplicate detection
- **Clusters** similar stories with Union-Find so only one representative gets LLM calls
- **Summarises** each cluster representative with an LLM (bullet points + meta description)
- **Tags** articles with topics, companies, and AI models (rule-based first, LLM fallback)
- **Scores** every article on four signals: importance, freshness, trend alignment, discussion breadth
- **Detects trends** by computing velocity-weighted sigmoid scores across tags, companies, and models
- **Generates** a daily brief (headline + summary + key themes) from the top articles
- **Publishes** a Next.js website with ISR, RSS feeds, full-text search, and structured data for SEO

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Pipeline (daily)                      │
│  Collect → Extract → Clean → Dedup → Cluster → Summarise   │
│  → Tag → Score → Store → Trends → Export → Brief           │
└─────────────────────┬───────────────────────────────────────┘
                       │ SQLite / PostgreSQL
┌─────────────────────▼───────────────────────────────────────┐
│                    FastAPI backend                           │
│  /api/v1/news  /briefs  /trends  /topics  /companies        │
│  /search  /rss  /stats  /pipeline                           │
└─────────────────────┬───────────────────────────────────────┘
                       │ HTTP (ISR)
┌─────────────────────▼───────────────────────────────────────┐
│                   Next.js frontend                           │
│  /  /trending  /daily/[date]  /news/[slug]                  │
│  /topics/[slug]  /companies/[slug]  /search                 │
└─────────────────────────────────────────────────────────────┘
```

## Repository layout

```
ai-signals/
├── backend/                  FastAPI application
│   ├── app/
│   │   ├── api/v1/           REST endpoints
│   │   ├── core/             database, logging, exceptions
│   │   ├── models/           SQLAlchemy ORM models
│   │   ├── pipeline/         12-stage pipeline + runner
│   │   │   └── stages/
│   │   ├── scheduler/        APScheduler worker + retry + health
│   │   ├── schemas/          Pydantic response schemas
│   │   └── services/
│   │       ├── crawler/      RSS fetcher, web scraper, content extractor
│   │       ├── llm/          OpenAI / Anthropic / DeepSeek / OpenRouter clients
│   │       ├── scoring/      importance, freshness, trend, discussion, ranker
│   │       └── trend/        aggregator, calculator, detector
│   ├── tests/                pytest test suite
│   ├── alembic/              database migrations
│   └── pyproject.toml
├── frontend/                 Next.js 14 App Router
│   ├── src/
│   │   ├── app/              pages + layouts + sitemap + robots
│   │   ├── components/       layout, news, brief, trends, ui
│   │   └── lib/              api client, types, utilities
│   └── vercel.json
├── scripts/
│   ├── manage.py             management CLI
│   ├── run_worker.py         standalone pipeline worker
│   └── seed_sources.py       seed 25 news sources
├── deploy/
│   ├── fly.backend.toml      Fly.io — API server
│   └── fly.worker.toml       Fly.io — pipeline worker
├── Dockerfile                multi-stage (backend-dev/prod, worker, frontend)
├── docker-compose.yml        local development
├── docker-compose.prod.yml   production compose
├── Makefile                  developer shortcuts
└── .github/workflows/
    ├── ci.yml                lint + test on every push
    ├── deploy.yml            build → push → deploy on main
    └── pipeline.yml          scheduled daily pipeline (GitHub Actions cron)
```

## Quick start

### Prerequisites

- Python 3.11+
- Node.js 20+
- An API key for at least one LLM provider (OpenAI recommended)

### 1. Clone and configure

```bash
git clone https://github.com/your-org/ai-signals
cd ai-signals

cp .env.example .env
# Edit .env — set OPENAI_API_KEY (or your preferred LLM provider)
```

### 2. Backend

```bash
cd backend
pip install -e ".[dev]"
cp .env.example .env   # fill in your keys

# Create tables and seed sources
python ../scripts/manage.py db seed

# Start the API server
uvicorn app.main:app --reload
# → http://localhost:8000
# → http://localhost:8000/api/docs
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:3000
```

### 4. Run the pipeline

```bash
# One-shot run (today's articles)
python scripts/manage.py pipeline run

# Or via Make
make pipeline
```

### Using Docker

```bash
# Copy and fill in .env with at minimum OPENAI_API_KEY
cp .env.example .env

# Start everything
make up
# Backend:  http://localhost:8000
# Frontend: http://localhost:3000

# With the standalone worker (optional — backend already runs scheduler)
make up-worker
```

## Configuration

All settings are environment variables. See `backend/.env.example` for the full list.

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `openai` | `openai` \| `anthropic` \| `deepseek` \| `openrouter` |
| `LLM_MODEL` | `gpt-4o-mini` | Model name for the chosen provider |
| `OPENAI_API_KEY` | — | Required when `LLM_PROVIDER=openai` |
| `DATABASE_URL` | SQLite (local) | `sqlite+aiosqlite:///./data/db/ai_signals.db` or `postgresql+asyncpg://...` |
| `PIPELINE_CRON` | `0 6 * * *` | Cron expression for daily run (UTC) |
| `PIPELINE_ENABLED` | `true` | Set `false` to pause scheduled runs |
| `PIPELINE_MIN_PUBLISH_SCORE` | `0.25` | Articles below this final score are not published |
| `LOG_FORMAT` | `console` | `console` (dev) or `json` (production) |

## Article scoring

Every article receives four sub-scores combined into a single `final_score`:

| Signal | Weight | Description |
|---|---|---|
| `importance_score` | 0.40 | Source authority + title signals + entity density + word count |
| `freshness_score` | 0.30 | Exponential decay, 24-hour half-life, 7-day max age |
| `trend_score` | 0.20 | Alignment with currently trending topics and companies |
| `discussion_score` | 0.10 | Cluster size proxy (how many similar articles exist) |

`final_score = importance×0.40 + freshness×0.30 + trend×0.20 + discussion×0.10`

Scores are normalised to [0, 1] via sigmoid. Articles with `final_score < PIPELINE_MIN_PUBLISH_SCORE` are stored but not published.

## Pipeline stages

| # | Stage | Description |
|---|---|---|
| 1 | `collect` | Fetch RSS feeds and web-scrape fallback sources concurrently |
| 2 | `extract` | Full-page extraction for articles with thin RSS content |
| 3 | `clean` | URL normalisation, slug generation, SimHash computation |
| 4 | `deduplicate` | Exact URL hash check (DB) + SimHash near-duplicate check (batch) |
| 5 | `cluster` | Union-Find grouping of similar articles; elect cluster representative |
| 6 | `summarise` | LLM summary + bullets for cluster reps only; non-reps inherit |
| 7 | `tag` | Rule-based tagging (free) + LLM tag/company/model extraction for reps |
| 8 | `score` | Compute all four sub-scores and `final_score` |
| 9 | `store` | Upsert articles, tags, companies, AI models to database |
| 10 | `detect_trends` | Compute trend velocity and update `TrendSnapshot` rows |
| 11 | `generate_pages` | Export JSON data files for frontend ISR |
| 12 | `generate_report` | LLM daily brief: headline, summary, key themes |

## LLM providers

Switch providers by setting `LLM_PROVIDER` and the corresponding API key:

```bash
# OpenAI (default)
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-...

# Anthropic
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-haiku-20240307
ANTHROPIC_API_KEY=sk-ant-...

# DeepSeek (cost-efficient)
LLM_PROVIDER=deepseek
LLM_MODEL=deepseek-chat
DEEPSEEK_API_KEY=sk-...

# OpenRouter (multi-model gateway)
LLM_PROVIDER=openrouter
LLM_MODEL=meta-llama/llama-3-8b-instruct
OPENROUTER_API_KEY=sk-or-...
```

LLM calls are minimised by only processing cluster representatives (~40% of articles). Non-representative articles inherit their cluster's summary and tags.

## API reference

The FastAPI backend auto-generates interactive docs at `/api/docs` (dev mode).

Key endpoints:

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/news` | Paginated article list (filter by tag, company, score) |
| `GET` | `/api/v1/news/top` | Top-scored articles |
| `GET` | `/api/v1/news/{slug}` | Article detail |
| `GET` | `/api/v1/briefs/latest` | Latest daily brief |
| `GET` | `/api/v1/briefs/{date}` | Brief for a specific date |
| `GET` | `/api/v1/trends/tags` | Trending topics |
| `GET` | `/api/v1/trends/companies` | Trending companies |
| `GET` | `/api/v1/search?q=` | Full-text search |
| `GET` | `/api/v1/rss` | RSS 2.0 main feed |
| `GET` | `/api/v1/rss/{tag}` | RSS feed per topic |
| `GET` | `/api/v1/stats` | Platform statistics |
| `POST` | `/api/v1/pipeline/trigger` | Trigger pipeline run |
| `GET` | `/api/v1/pipeline/scheduler` | Scheduler status |

## Management CLI

```bash
# Run pipeline for today
python scripts/manage.py pipeline run

# Run for a specific past date
python scripts/manage.py pipeline run --date 2026-03-01

# Backfill a date range
python scripts/manage.py pipeline backfill --from 2026-02-01 --to 2026-02-28

# Show recent run history
python scripts/manage.py pipeline status

# Database
python scripts/manage.py db migrate   # alembic upgrade head
python scripts/manage.py db seed      # seed news sources

# Sources
python scripts/manage.py sources list
python scripts/manage.py sources enable arxiv
python scripts/manage.py sources disable techcrunch
```

## Deployment

### Fly.io (backend + worker)

```bash
# Install flyctl, then:
fly apps create ai-signals-api
fly volumes create ai_signals_data --size 3 --region lax --app ai-signals-api
fly secrets set \
  SECRET_KEY="$(openssl rand -hex 32)" \
  OPENAI_API_KEY="sk-..." \
  --app ai-signals-api

make deploy-backend

# Optional dedicated worker
fly apps create ai-signals-worker
fly secrets set OPENAI_API_KEY="sk-..." --app ai-signals-worker
make deploy-worker
```

### Vercel (frontend)

```bash
cd frontend
vercel deploy --prod
# Set NEXT_PUBLIC_API_URL to your Fly.io backend URL in the Vercel dashboard
```

### GitHub Actions secrets required

| Secret | Used by |
|---|---|
| `FLY_API_TOKEN` | `deploy.yml` |
| `VERCEL_TOKEN` | `deploy.yml` |
| `VERCEL_ORG_ID` | `deploy.yml` |
| `VERCEL_PROJECT_ID` | `deploy.yml` |
| `OPENAI_API_KEY` | `pipeline.yml` (scheduled cron) |
| `DATABASE_URL` | `pipeline.yml` (scheduled cron) |

### Zero-infrastructure option

Skip Fly.io entirely. Use the GitHub Actions scheduled pipeline (`pipeline.yml`) with a remote PostgreSQL database (Supabase free tier, Neon, or Railway). The pipeline runs in a GitHub-hosted runner at 06:00 UTC — no always-on server required.

## Development

```bash
make test          # backend pytest + frontend tsc/eslint
make lint          # ruff + eslint
make format        # ruff format + autofix
make pipeline      # run pipeline now
make help          # all available targets
```

### Adding a news source

Edit `scripts/seed_sources.py` and add an entry to `SOURCES`. Re-run `make seed`.
Source types: `rss` (preferred), `web` (CSS-selector scraping), `api`.

### Adding an LLM provider

1. Create `backend/app/services/llm/yourprovider_client.py` extending `BaseLLMClient`
2. Add a case to `services/llm/factory.py`
3. Add the API key field to `app/config.py`

## Tech stack

**Backend:** Python 3.11, FastAPI, SQLAlchemy 2.0 (async), Alembic, APScheduler, structlog, httpx, feedparser, readability-lxml, tenacity

**LLM:** OpenAI, Anthropic, DeepSeek, OpenRouter (pluggable via `BaseLLMClient`)

**Frontend:** Next.js 14 (App Router), React 18, TypeScript, Tailwind CSS, date-fns

**Database:** SQLite (development), PostgreSQL via asyncpg (production)

**Infrastructure:** Docker, Fly.io, Vercel, GitHub Actions

## License

MIT
