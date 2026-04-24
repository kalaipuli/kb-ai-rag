# Enterprise Agentic Knowledge Base — RAG Platform (Summary)

## Purpose

Build a production-ready **agentic RAG system** that evolves from a simple retrieval pipeline (MVP) into a **multi-agent, self-correcting knowledge system** with enterprise connectors, observability, and Azure deployment.

> For implementation details, edge cases, and exact configs → refer to `PROJECT_PLAN.md`.

---

## Core Stack

* **LLM:** Azure OpenAI (GPT-4o, embeddings)
* **Vector DB:** Qdrant (hybrid search: dense + BM25 + re-ranking)
* **Frameworks:** LangChain + LangGraph
* **Backend:** FastAPI (Python 3.12)
* **Frontend:** Next.js
* **Infra:** Docker (MVP) → Azure Container Apps (prod)

---

## System Architecture (Conceptual)

1. **Client Layer:** UI / API / CLI
2. **Agent Layer (LangGraph):**

   * Router → Retriever → Grader → Generator → Critic
   * Supports fallback (web search) and self-correction
3. **Retrieval Layer:**

   * Dense (Qdrant) + Sparse (BM25) → RRF fusion → Re-ranker
4. **Data Sources:**

   * MVP: Local files
   * Prod: Azure Blob + Azure AI Search
5. **Platform:** Azure (OpenAI, Storage, Monitoring, Containers)

---

## Delivery Strategy (Phased)

### Phase 0 — Foundation

* Project setup, CI, logging, Docker
* No AI logic yet

### Phase 1 — MVP RAG

* File ingestion → chunking → embeddings → Qdrant
* Hybrid retrieval + basic LLM answer generation
* API + simple UI
* Evaluation baseline (RAGAS)

👉 Outcome: Working end-to-end RAG system

---

### Phase 2 — Agentic System

* Replace pipeline with **LangGraph agents**
* Add:

  * Query routing
  * Document grading
  * Hallucination detection (critic)
  * Fallback web search (CRAG)
* Introduce conversational memory

👉 Outcome: System can reason, not just retrieve

---

### Phase 3 — Enterprise Data

* Azure Blob ingestion
* Azure AI Search connector
* Multi-source retrieval via abstraction layer

---

### Phase 4 — Multi-Hop Reasoning

* Query decomposition
* Parallel retrieval
* Answer synthesis
* Optional human-in-the-loop

---

### Phase 5 — Observability & Evaluation

* LangSmith tracing
* Automated RAG evaluation (RAGAS)
* Metrics: latency, cost, quality

---

### Phase 6 — Production Hardening

* Auth (Azure AD)
* Prompt injection protection
* Rate limiting, retries, circuit breakers
* Async ingestion pipeline

---

### Phase 7 — Deployment

* Terraform infrastructure
* CI/CD pipeline
* Azure Container Apps deployment

---

## Key Capabilities

* Hybrid semantic + keyword retrieval
* Self-correcting answers (critic loop)
* Adaptive retrieval strategies
* Multi-source knowledge integration
* Multi-hop reasoning (complex queries)
* Observability + evaluation baked in

---

## API Surface (MVP)

* `POST /ingest` — load documents
* `POST /query` — ask questions
* `GET /health` — system status

---

## Success Criteria (MVP)

* End-to-end ingestion + query working
* < 8s response time (local)
* Grounded answers with citations
* Evaluation baseline established

---

## Important Notes for LLM Usage

* This is a **high-level plan only**
* Do NOT assume implementation specifics from this summary
* For:

  * exact schemas
  * agent state definitions
  * config details
  * prompts
  * infra setup

👉 Always refer to `PROJECT_PLAN.md`

---

## Open Dependencies

* Azure OpenAI access
* Optional: Tavily (web search), LangSmith (observability)
* Sample dataset for ingestion

---

## Mental Model

Think of the system evolving as:

**Search → RAG → Agent → Reasoning System → Production Platform**
