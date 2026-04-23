# Project Goal

## Why This Project Exists

To land an **AI Architect** role by demonstrating that I can design, build, evaluate, and deploy a production-grade agentic AI system — not just wire together tutorials.

The system must show:
- Architectural judgment (why these choices, what are the trade-offs)
- Production thinking (auth, observability, evaluation, error handling)
- AI depth (agentic patterns beyond basic RAG, not just a chatbot)
- Cloud fluency (Azure-native deployment, managed services, IaC)
- Engineering discipline (typed code, CI/CD, ADRs, test coverage)

---

## What Success Looks Like

### For the Portfolio
- A public GitHub repo that an AI Architect hiring manager can read in 20 minutes and understand the system design, not just the code
- A live demo (or recorded walkthrough) that shows the agent working on real knowledge articles
- Architecture Decision Records that show how trade-offs were reasoned through
- RAGAS evaluation results proving the system actually works

### For Interviews
- Can explain every architectural choice and what was considered but rejected
- Can walk through a LangGraph agent trace and explain each decision node
- Can speak to production concerns: ACL, prompt injection, circuit breakers, cost
- Can discuss what would change at 10x scale

---

## Non-Negotiables

| Requirement | Reason |
|-------------|--------|
| Agentic, not just RAG | Basic RAG is a solved, commoditized problem. Agents show architect-level thinking. |
| Evaluation with numbers | Any claim about quality must be backed by RAGAS scores on a golden dataset. |
| Azure deployment | The target role requires Azure fluency. Local-only is not sufficient. |
| Open-source vector DB | Shows ability to work outside managed-only solutions (Qdrant, not just Pinecone). |
| Architecture docs and ADRs | Architects communicate decisions in writing. Code alone is not enough. |
| Typed, linted Python | No notebook-quality code in the repo. Production standards throughout. |

---

## The Narrative for Interviews

> "I built an agentic knowledge retrieval platform that connects to enterprise sources — local files in development, Azure Blob and Azure AI Search in production. A LangGraph state machine orchestrates five specialized agents: a router that classifies query intent, a retriever that selects the right source, a grader that scores chunk relevance, a generator that produces cited answers, and a critic that checks for hallucination before returning a response. When retrieval quality is poor, the system falls back to web search automatically. I evaluated quality with RAGAS throughout development and gated each phase on a minimum faithfulness threshold."

---

## Constraints

- **Solo build** — no team, no shortcuts on architecture quality
- **Time-boxed** — ~7 weeks total, phased to always have something demo-able
- **Cost-aware** — GPT-4o only for final generation; cheaper models for grading/routing where quality allows
- **Open source preferred** — Qdrant over Pinecone, LangGraph over proprietary orchestrators

---

## What This Is NOT

- A research project — it ships
- A tutorial follow-along — every pattern is implemented with production constraints in mind
- A notebook — it is a deployable service with an API
- A one-source system — the connector architecture is designed for extensibility
