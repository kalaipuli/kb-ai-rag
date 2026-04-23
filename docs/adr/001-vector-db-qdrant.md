# ADR-001: Qdrant as the Vector Database

## Status
Accepted

## Context
The platform needs a vector database for storing and retrieving dense embeddings of document chunks. Key requirements include:
- Self-hosted option for portfolio portability and cost control
- Native hybrid search combining dense (embedding) and sparse (BM25/keyword) retrieval
- Rich payload filtering to enable metadata-driven retrieval without domain-specific routing
- Active open-source development with a stable API
- Local development via Docker with a path to production cloud deployment

## Decision
Use Qdrant as the vector database, self-hosted via Docker in development and optionally via Qdrant Cloud in production.

## Alternatives Considered

**Pinecone**: Fully managed SaaS offering. Rejected because it is managed-only (no self-hosted option), introduces vendor lock-in, has no native BM25 sparse vector support in the base offering, and is not differentiated from a portfolio perspective — it demonstrates managed service consumption, not architectural judgment.

**Weaviate**: Open-source, self-hosted capable. Rejected because its hybrid search was less mature at the time of selection, its resource footprint is heavier than Qdrant for equivalent workloads, and its GraphQL query interface adds unnecessary complexity for this use case.

**pgvector (PostgreSQL extension)**: Rejected because it lacks a dedicated vector index (HNSW performance degrades at scale without careful tuning), has no native BM25 sparse search capability, and conflates relational and vector concerns. The architecture uses no relational database by design.

**Azure AI Search**: Considered as the vector store. Rejected for Phase 0/1 because it requires provisioning an Azure resource, which blocks local development. It remains a secondary retrieval source in Phase 3 via the BaseRetriever abstraction.

## Consequences

**Positive:**
- Self-hosted Docker image means no cloud account required for local development or portfolio demos
- Qdrant's native sparse vector support (SPLADE/BM25) means the BM25 index can migrate into Qdrant in a future phase, eliminating the in-memory BM25 index
- Rich payload filtering on chunk metadata (filename, file_type, tags, source_path) enables metadata-driven retrieval without domain routing
- No vendor lock-in: Qdrant Cloud is drop-in compatible with the self-hosted API

**Negative:**
- Self-hosted means owning operational complexity (backup, persistence, scaling) in production; mitigated by Qdrant Cloud as an option
- Qdrant version must be pinned in Docker Compose to avoid breaking API changes between releases
