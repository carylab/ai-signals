# AI Signals — developer Makefile
# Usage: make <target>

.PHONY: help dev dev-backend dev-frontend \
        build up down logs \
        test test-backend test-frontend \
        lint format \
        migrate seed \
        pipeline pipeline-date \
        deploy-backend deploy-worker deploy-frontend \
        clean

PYTHON  := python3
PIP     := pip
NPM     := npm
BACKEND := backend
FRONTEND:= frontend
SCRIPTS := scripts

# Colour helpers
BOLD := \033[1m
RESET:= \033[0m

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | sort \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(BOLD)%-22s$(RESET) %s\n", $$1, $$2}'

# ── Local development (no Docker) ────────────────────────────────────────────

dev: ## Start backend + frontend in parallel (tmux/foreman style)
	@echo "Starting backend on :8000 and frontend on :3000"
	@$(MAKE) -j2 dev-backend dev-frontend

dev-backend: ## Start FastAPI dev server
	cd $(BACKEND) && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend: ## Start Next.js dev server
	cd $(FRONTEND) && $(NPM) run dev

# ── Docker workflows ──────────────────────────────────────────────────────────

build: ## Build all Docker images
	docker compose build

up: ## Start all services
	docker compose up -d

up-worker: ## Start all services including the worker profile
	docker compose --profile worker up -d

down: ## Stop all services
	docker compose down

logs: ## Tail logs (all services)
	docker compose logs -f

logs-backend: ## Tail backend logs
	docker compose logs -f backend

logs-worker: ## Tail worker logs
	docker compose logs -f worker

# ── Testing ───────────────────────────────────────────────────────────────────

test: test-backend test-frontend ## Run all tests

test-backend: ## Run backend tests
	cd $(BACKEND) && \
	  APP_ENV=test \
	  DATABASE_URL="sqlite+aiosqlite:///:memory:" \
	  LLM_PROVIDER=openai \
	  OPENAI_API_KEY=sk-test \
	  pytest -v --tb=short

test-frontend: ## TypeScript type-check + Next.js lint
	cd $(FRONTEND) && $(NPM) run type-check && $(NPM) run lint

# ── Linting / Formatting ──────────────────────────────────────────────────────

lint: ## Lint backend (ruff) and frontend (eslint)
	cd $(BACKEND) && ruff check .
	cd $(FRONTEND) && $(NPM) run lint

format: ## Auto-format backend code
	cd $(BACKEND) && ruff format . && ruff check --fix .

# ── Database ──────────────────────────────────────────────────────────────────

migrate: ## Run Alembic migrations
	cd $(BACKEND) && alembic upgrade head

seed: ## Seed news sources into the database
	cd $(BACKEND) && $(PYTHON) ../$(SCRIPTS)/manage.py db seed

# ── Pipeline ──────────────────────────────────────────────────────────────────

pipeline: ## Run pipeline for today
	$(PYTHON) $(SCRIPTS)/manage.py pipeline run

pipeline-date: ## Run pipeline for DATE=YYYY-MM-DD  (e.g. make pipeline-date DATE=2026-03-01)
	$(PYTHON) $(SCRIPTS)/manage.py pipeline run --date $(DATE)

pipeline-status: ## Show recent pipeline run history
	$(PYTHON) $(SCRIPTS)/manage.py pipeline status

pipeline-backfill: ## Backfill FROM=YYYY-MM-DD TO=YYYY-MM-DD
	$(PYTHON) $(SCRIPTS)/manage.py pipeline backfill --from $(FROM) --to $(TO)

sources: ## List all news sources
	$(PYTHON) $(SCRIPTS)/manage.py sources list

# ── Deployment ────────────────────────────────────────────────────────────────

deploy-backend: ## Deploy backend to Fly.io
	flyctl deploy --config deploy/fly.backend.toml --remote-only

deploy-worker: ## Deploy worker to Fly.io
	flyctl deploy --config deploy/fly.worker.toml --remote-only

deploy-frontend: ## Deploy frontend to Vercel
	cd $(FRONTEND) && vercel deploy --prod

# ── Maintenance ───────────────────────────────────────────────────────────────

clean: ## Remove build artefacts and caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf $(FRONTEND)/.next $(FRONTEND)/node_modules/.cache 2>/dev/null || true
	@echo "Clean complete."
