# Deployment Guide

## Prerequisites

- Docker and Docker Compose installed
- Azure OpenAI resource with two deployed models:
  - A chat model (e.g. `gpt-4o`)
  - An embedding model (e.g. `text-embedding-ada-002`)

---

## 1. Configure the Backend

Copy the example env file and fill in your Azure credentials:

```bash
cp backend/.env.example backend/.env
```

Required values in `backend/.env`:

| Variable | Description |
|---|---|
| `AZURE_OPENAI_ENDPOINT` | Your Azure OpenAI endpoint URL |
| `AZURE_OPENAI_API_KEY` | Your Azure OpenAI API key |
| `AZURE_CHAT_DEPLOYMENT` | Chat model deployment name |
| `AZURE_EMBEDDING_DEPLOYMENT` | Embedding model deployment name |
| `API_KEY` | A secure random string — used to authenticate frontend requests |

All other values have working defaults for Docker Compose. Do not change `QDRANT_URL`, `DATA_DIR`, or `BM25_INDEX_PATH` for Docker deployments.

---

## 2. Configure the Frontend

```bash
cp frontend/.env.example frontend/.env
```

Set `API_KEY` to the same value you used in the backend `.env`.

---

## 3. Build and Start

From the `infra/` directory:

```bash
cd infra
docker compose up --build
```

This starts three services in order: **Qdrant → Backend → Frontend**.

Startup takes 1–2 minutes on first run (model download for the reranker). The stack is ready when you see the frontend container log `ready on port 3000`.

| Service | URL |
|---|---|
| Frontend (chat UI) | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| Qdrant dashboard | http://localhost:6333/dashboard |

---

## 4. Ingest Knowledge Articles

Place PDF or `.txt` files in `backend/data/knowledge/`, then call the ingest endpoint:

```bash
curl -X POST http://localhost:8000/api/v1/ingest \
  -H "X-API-Key: <your-api-key>" \
  -H "Content-Type: application/json" \
  -d '{"collection": "kb_documents"}'
```

The backend will chunk, embed, and index all files in `data/knowledge/`. Re-run after adding new files.

---

## 5. Stop the Stack

```bash
docker compose down
```

Qdrant data persists in the host volume (`/Users/<you>/qdrant_storage` by default). Edit the volume path in `infra/docker-compose.yml` to change this.
