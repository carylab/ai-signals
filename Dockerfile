# ── Backend ───────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS backend-base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# System deps for lxml / readability-lxml
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libxml2-dev \
        libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps (layer-cached separately from code)
COPY backend/pyproject.toml .
RUN pip install --no-deps -e . 2>/dev/null || pip install .

# ── Dev stage (includes dev extras, no code copy) ────────────────────────────
FROM backend-base AS backend-dev

RUN pip install "pytest>=8.2.0" "pytest-asyncio>=0.23.6" \
                "pytest-httpx>=0.30.0" "ruff>=0.4.4" "mypy>=1.10.0" \
                "factory-boy>=3.3.0"

COPY backend/ .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ── Production web server ─────────────────────────────────────────────────────
FROM backend-base AS backend-prod

COPY backend/ .

# Create data directories
RUN mkdir -p /app/data/db /app/data/exports

# Non-root user
RUN useradd -r -u 1001 -g root appuser \
    && chown -R appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "2", \
     "--access-log"]

# ── Pipeline worker ───────────────────────────────────────────────────────────
FROM backend-prod AS worker

# Worker runs as daemon (no HTTP port needed)
EXPOSE 8001

CMD ["python", "scripts/run_worker.py"]

# ── Frontend ──────────────────────────────────────────────────────────────────
FROM node:20-alpine AS frontend-deps

WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci

FROM frontend-deps AS frontend-build

WORKDIR /app
COPY frontend/ .
RUN npm run build

FROM node:20-alpine AS frontend-prod

WORKDIR /app
ENV NODE_ENV=production

COPY --from=frontend-build /app/.next/standalone ./
COPY --from=frontend-build /app/.next/static ./.next/static
COPY --from=frontend-build /app/public ./public

RUN addgroup -S appgroup && adduser -S appuser -G appgroup
USER appuser

EXPOSE 3000
ENV PORT=3000 HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
