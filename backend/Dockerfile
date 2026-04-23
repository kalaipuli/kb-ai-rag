FROM python:3.12-slim AS base
WORKDIR /app

RUN pip install --no-cache-dir poetry==1.8.4
ENV POETRY_VIRTUALENVS_CREATE=false

COPY pyproject.toml poetry.lock* ./
RUN poetry install --no-interaction --only main

RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --ingroup appgroup appuser

COPY src/ ./src/

RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "warning"]
