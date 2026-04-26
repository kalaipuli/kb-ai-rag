# ── Stage 1: dependency builder ──────────────────────────────────────────────
FROM python:3.12-slim AS builder

ENV POETRY_VERSION=1.8.4 \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1

RUN pip install --no-cache-dir poetry==${POETRY_VERSION}

WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN poetry install --only main --no-root

# ── Stage 2: runtime ─────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

RUN addgroup --system --gid 1001 appgroup \
    && adduser --system --uid 1001 --ingroup appgroup appuser

WORKDIR /app

COPY --from=builder --chown=appuser:appgroup /app/.venv /app/.venv
COPY --chown=appuser:appgroup src/ ./src/

RUN mkdir -p /app/cache && chown appuser:appgroup /app/cache

ENV PATH="/app/.venv/bin:$PATH" \
    HOME=/app \
    HF_HOME=/app/cache \
    HF_HUB_CACHE=/app/cache/hub \
    NLTK_DATA=/app/cache/nltk

# Download NLTK punkt_tab data required by SentenceWindowSplitter.
# Running as root before USER switch so the cache directory is writable.
RUN python -m nltk.downloader -d /app/cache/nltk punkt_tab

USER appuser

EXPOSE 8000
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "warning"]
