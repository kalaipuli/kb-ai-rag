# KB AI RAG

An enterprise agentic RAG system for querying internal knowledge bases using natural language. Built with LangGraph, FastAPI, Qdrant, and Next.js.

---

## How it works

Documents (PDFs, text files) are ingested, chunked, and indexed in a hybrid vector + BM25 store. A LangGraph agent pipeline handles retrieval, reranking, and answer generation with source citations. A streaming chat UI delivers responses in real time.

---

## Stack

| Layer | Technology |
|---|---|
| LLM / Embeddings | Azure OpenAI (GPT-4o + text-embedding-ada-002) |
| Vector store | Qdrant |
| Agent orchestration | LangGraph |
| Backend | FastAPI (Python) |
| Frontend | Next.js (TypeScript) |
| Evaluation | RAGAS |

---

## Documentation

| Guide | Description |
|---|---|
| [Deployment Guide](docs/deployment-guide.md) | Build Docker images, configure env vars, start the stack |
| [Test Guide](docs/test-guide.md) | Run backend and frontend tests, RAGAS evaluation |
| [User Guide](docs/user-guide.md) | Chat interface features and usage |

---

## Quick Start

```bash
# 1. Configure credentials
cp backend/.env.example backend/.env   # fill in Azure keys + API_KEY
cp frontend/.env.example frontend/.env # set matching API_KEY

# 2. Start the stack
cd infra && docker compose up --build

# 3. Open the app
open http://localhost:3000
```

See the [Deployment Guide](docs/deployment-guide.md) for ingest instructions and full configuration details.
