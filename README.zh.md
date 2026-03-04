# AI Signals

自动化 AI 行业情报平台。每日抓取全球 AI 资讯，经过多阶段 LLM 流水线处理，对文章进行评分排名、趋势检测，并发布包含每日简报的网站。

## 功能概览

- **抓取** 25+ 个 AI 新闻源（RSS 和网页爬虫），每天 06:00 UTC 自动执行
- **去重** 通过 URL 哈希和 SimHash 近似去重检测重复文章
- **聚类** 使用 Union-Find 算法对相似文章分组，每组只调用一次 LLM
- **摘要** 用 LLM 为每个聚类代表生成摘要（要点 + 元描述）
- **标签** 对文章打上话题、公司、AI 模型标签（优先规则匹配，兜底 LLM 提取）
- **评分** 对每篇文章按四个维度打分：重要性、新鲜度、趋势契合度、讨论广度
- **趋势检测** 对标签、公司、模型计算速度加权 sigmoid 分数，更新趋势快照
- **生成** 每日简报（标题 + 摘要 + 关键主题），来自评分最高的文章
- **发布** 基于 Next.js 的网站，支持 ISR、RSS 订阅、全文搜索和 SEO 结构化数据

## 架构

```
┌─────────────────────────────────────────────────────────────┐
│                        流水线（每日）                         │
│  采集 → 提取 → 清洗 → 去重 → 聚类 → 摘要                     │
│  → 标签 → 评分 → 入库 → 趋势 → 导出 → 简报                   │
└─────────────────────┬───────────────────────────────────────┘
                       │ SQLite / PostgreSQL
┌─────────────────────▼───────────────────────────────────────┐
│                    FastAPI 后端                               │
│  /api/v1/news  /briefs  /trends  /topics  /companies        │
│  /search  /rss  /stats  /pipeline                           │
└─────────────────────┬───────────────────────────────────────┘
                       │ HTTP（ISR）
┌─────────────────────▼───────────────────────────────────────┐
│                   Next.js 前端                               │
│  /  /trending  /daily/[date]  /news/[slug]                  │
│  /topics/[slug]  /companies/[slug]  /search                 │
└─────────────────────────────────────────────────────────────┘
```

## 目录结构

```
ai-signals/
├── backend/                  FastAPI 应用
│   ├── app/
│   │   ├── api/v1/           REST 接口
│   │   ├── core/             数据库、日志、异常
│   │   ├── models/           SQLAlchemy ORM 模型
│   │   ├── pipeline/         12 阶段流水线 + 调度器
│   │   │   └── stages/
│   │   ├── scheduler/        APScheduler 工作进程 + 重试 + 健康检查
│   │   ├── schemas/          Pydantic 响应结构
│   │   └── services/
│   │       ├── crawler/      RSS 抓取、网页爬虫、内容提取
│   │       ├── llm/          OpenAI / Anthropic / DeepSeek / OpenRouter 客户端
│   │       ├── scoring/      重要性、新鲜度、趋势、讨论度评分 + 排名器
│   │       └── trend/        聚合器、计算器、检测器
│   ├── tests/                pytest 测试套件
│   ├── alembic/              数据库迁移
│   └── pyproject.toml
├── frontend/                 Next.js 14 App Router
│   ├── src/
│   │   ├── app/              页面 + 布局 + sitemap + robots
│   │   ├── components/       layout、news、brief、trends、ui 组件
│   │   └── lib/              API 客户端、类型定义、工具函数
│   └── vercel.json
├── scripts/
│   ├── manage.py             管理命令行工具
│   ├── run_worker.py         独立流水线 worker
│   └── seed_sources.py       初始化 25 个新闻源
├── deploy/
│   ├── fly.backend.toml      Fly.io — API 服务器
│   └── fly.worker.toml       Fly.io — 流水线 worker
├── Dockerfile                多阶段构建（backend-dev/prod、worker、frontend）
├── docker-compose.yml        本地开发环境
├── docker-compose.prod.yml   生产环境 compose
├── Makefile                  开发者快捷命令
└── .github/workflows/
    ├── ci.yml                每次推送时执行 lint + 测试
    ├── deploy.yml            主分支：构建 → 推送 → 部署
    └── pipeline.yml          GitHub Actions 定时每日流水线
```

## 快速开始

### 前置要求

- Python 3.11+
- Node.js 20+
- 至少一个 LLM 提供商的 API 密钥（推荐 OpenAI）

### 1. 克隆并配置

```bash
git clone https://github.com/your-org/ai-signals
cd ai-signals

cp .env.example .env
# 编辑 .env，设置 OPENAI_API_KEY（或你偏好的 LLM 提供商）
```

### 2. 后端

```bash
cd backend
pip install -e ".[dev]"
cp .env.example .env   # 填入你的密钥

# 创建数据表并初始化数据源
python ../scripts/manage.py db seed

# 启动 API 服务器
uvicorn app.main:app --reload
# → http://localhost:8000
# → http://localhost:8000/api/docs
```

### 3. 前端

```bash
cd frontend
npm install
npm run dev
# → http://localhost:3000
```

### 4. 运行流水线

```bash
# 单次运行（处理今天的文章）
python scripts/manage.py pipeline run

# 或通过 Make
make pipeline
```

### 使用 Docker

```bash
# 复制并填写 .env，至少设置 OPENAI_API_KEY
cp .env.example .env

# 启动所有服务
make up
# 后端：http://localhost:8000
# 前端：http://localhost:3000

# 启动独立 worker（可选，后端已内置调度器）
make up-worker
```

## 配置说明

所有配置均通过环境变量设置，完整列表见 `backend/.env.example`。

| 变量 | 默认值 | 说明 |
|---|---|---|
| `LLM_PROVIDER` | `openai` | `openai` \| `anthropic` \| `deepseek` \| `openrouter` |
| `LLM_MODEL` | `gpt-4o-mini` | 所选提供商的模型名称 |
| `OPENAI_API_KEY` | — | `LLM_PROVIDER=openai` 时必填 |
| `DATABASE_URL` | SQLite（本地） | `sqlite+aiosqlite:///./data/db/ai_signals.db` 或 `postgresql+asyncpg://...` |
| `PIPELINE_CRON` | `0 6 * * *` | 每日运行的 cron 表达式（UTC） |
| `PIPELINE_ENABLED` | `true` | 设为 `false` 可暂停定时运行 |
| `PIPELINE_MIN_PUBLISH_SCORE` | `0.25` | 低于此最终分数的文章不会发布 |
| `LOG_FORMAT` | `console` | `console`（开发）或 `json`（生产） |

## 文章评分

每篇文章的四个子分数合并为一个 `final_score`：

| 信号 | 权重 | 说明 |
|---|---|---|
| `importance_score` | 0.40 | 来源权威度 + 标题信号 + 实体密度 + 字数 |
| `freshness_score` | 0.30 | 指数衰减，24 小时半衰期，最大 7 天 |
| `trend_score` | 0.20 | 与当前热门话题和公司的契合度 |
| `discussion_score` | 0.10 | 聚类大小代理（相似文章数量） |

`final_score = importance×0.40 + freshness×0.30 + trend×0.20 + discussion×0.10`

分数通过 sigmoid 归一化到 [0, 1]。`final_score < PIPELINE_MIN_PUBLISH_SCORE` 的文章会入库但不发布。

## 流水线阶段

| # | 阶段 | 说明 |
|---|---|---|
| 1 | `collect` | 并发抓取 RSS 和网页爬虫备用源 |
| 2 | `extract` | 对 RSS 内容较少的文章进行全文提取 |
| 3 | `clean` | URL 规范化、slug 生成、SimHash 计算 |
| 4 | `deduplicate` | 精确 URL 哈希检查（数据库）+ SimHash 近似去重（批量） |
| 5 | `cluster` | Union-Find 相似文章分组，选出聚类代表 |
| 6 | `summarise` | 仅对聚类代表生成 LLM 摘要 + 要点；非代表继承聚类摘要 |
| 7 | `tag` | 规则匹配标签（免费）+ LLM 提取代表的标签/公司/模型 |
| 8 | `score` | 计算四个子分数和 `final_score` |
| 9 | `store` | 将文章、标签、公司、AI 模型 upsert 到数据库 |
| 10 | `detect_trends` | 计算趋势速度并更新 `TrendSnapshot` 记录 |
| 11 | `generate_pages` | 导出前端 ISR 所需的 JSON 数据文件 |
| 12 | `generate_report` | LLM 每日简报：标题、摘要、关键主题 |

## LLM 提供商

通过设置 `LLM_PROVIDER` 和对应 API 密钥来切换提供商：

```bash
# OpenAI（默认）
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-...

# Anthropic
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-haiku-20240307
ANTHROPIC_API_KEY=sk-ant-...

# DeepSeek（性价比高）
LLM_PROVIDER=deepseek
LLM_MODEL=deepseek-chat
DEEPSEEK_API_KEY=sk-...

# OpenRouter（多模型网关）
LLM_PROVIDER=openrouter
LLM_MODEL=meta-llama/llama-3-8b-instruct
OPENROUTER_API_KEY=sk-or-...
```

通过只处理聚类代表（约占 40% 的文章），LLM 调用次数被大幅降低。非代表文章继承其聚类的摘要和标签。

## API 参考

FastAPI 后端在 `/api/docs` 自动生成交互式文档（开发模式）。

主要接口：

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/v1/news` | 分页文章列表（支持按标签、公司、分数筛选） |
| `GET` | `/api/v1/news/top` | 评分最高的文章 |
| `GET` | `/api/v1/news/{slug}` | 文章详情 |
| `GET` | `/api/v1/briefs/latest` | 最新每日简报 |
| `GET` | `/api/v1/briefs/{date}` | 指定日期的简报 |
| `GET` | `/api/v1/trends/tags` | 热门话题 |
| `GET` | `/api/v1/trends/companies` | 热门公司 |
| `GET` | `/api/v1/search?q=` | 全文搜索 |
| `GET` | `/api/v1/rss` | RSS 2.0 主订阅 |
| `GET` | `/api/v1/rss/{tag}` | 按话题的 RSS 订阅 |
| `GET` | `/api/v1/stats` | 平台统计数据 |
| `POST` | `/api/v1/pipeline/trigger` | 手动触发流水线 |
| `GET` | `/api/v1/pipeline/scheduler` | 调度器状态 |

## 管理命令行

```bash
# 运行今天的流水线
python scripts/manage.py pipeline run

# 运行指定历史日期
python scripts/manage.py pipeline run --date 2026-03-01

# 回填日期范围
python scripts/manage.py pipeline backfill --from 2026-02-01 --to 2026-02-28

# 查看最近运行历史
python scripts/manage.py pipeline status

# 数据库
python scripts/manage.py db migrate   # alembic upgrade head
python scripts/manage.py db seed      # 初始化新闻源

# 数据源管理
python scripts/manage.py sources list
python scripts/manage.py sources enable arxiv
python scripts/manage.py sources disable techcrunch
```

## 部署

### Fly.io（后端 + worker）

```bash
# 安装 flyctl，然后执行：
fly apps create ai-signals-api
fly volumes create ai_signals_data --size 3 --region lax --app ai-signals-api
fly secrets set \
  SECRET_KEY="$(openssl rand -hex 32)" \
  OPENAI_API_KEY="sk-..." \
  --app ai-signals-api

make deploy-backend

# 可选：独立 worker
fly apps create ai-signals-worker
fly secrets set OPENAI_API_KEY="sk-..." --app ai-signals-worker
make deploy-worker
```

### Vercel（前端）

```bash
cd frontend
vercel deploy --prod
# 在 Vercel 控制台中将 NEXT_PUBLIC_API_URL 设置为你的 Fly.io 后端地址
```

### GitHub Actions 所需 Secrets

| Secret | 用途 |
|---|---|
| `FLY_API_TOKEN` | `deploy.yml` |
| `VERCEL_TOKEN` | `deploy.yml` |
| `VERCEL_ORG_ID` | `deploy.yml` |
| `VERCEL_PROJECT_ID` | `deploy.yml` |
| `OPENAI_API_KEY` | `pipeline.yml`（定时 cron） |
| `DATABASE_URL` | `pipeline.yml`（定时 cron） |

### 零基础设施方案

完全跳过 Fly.io。使用 GitHub Actions 定时流水线（`pipeline.yml`）配合远程 PostgreSQL 数据库（Supabase 免费套餐、Neon 或 Railway）。流水线在 GitHub 托管的 runner 上每天 06:00 UTC 运行——无需常驻服务器。

## 开发

```bash
make test          # 后端 pytest + 前端 tsc/eslint
make lint          # ruff + eslint
make format        # ruff format + 自动修复
make pipeline      # 立即运行流水线
make help          # 查看所有可用命令
```

### 添加新闻源

编辑 `scripts/seed_sources.py`，在 `SOURCES` 中添加条目，然后重新运行 `make seed`。
数据源类型：`rss`（首选）、`web`（CSS 选择器爬虫）、`api`。

### 添加 LLM 提供商

1. 创建 `backend/app/services/llm/yourprovider_client.py`，继承 `BaseLLMClient`
2. 在 `services/llm/factory.py` 中添加对应 case
3. 在 `app/config.py` 中添加 API 密钥字段

## 技术栈

**后端：** Python 3.11、FastAPI、SQLAlchemy 2.0（async）、Alembic、APScheduler、structlog、httpx、feedparser、readability-lxml、tenacity

**LLM：** OpenAI、Anthropic、DeepSeek、OpenRouter（通过 `BaseLLMClient` 可插拔扩展）

**前端：** Next.js 14（App Router）、React 18、TypeScript、Tailwind CSS、date-fns

**数据库：** SQLite（开发）、PostgreSQL via asyncpg（生产）

**基础设施：** Docker、Fly.io、Vercel、GitHub Actions

## 许可证

MIT
