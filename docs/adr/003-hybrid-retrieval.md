# ADR-003: Hybrid Retrieval with RRF Fusion (Dense + BM25)

## Status
Accepted

## Context
Knowledge base articles frequently contain exact model names, error codes, configuration keys, version numbers, and product identifiers. Examples: "AKS node pool autoscaler error 0x800704B3", "text-embedding-3-large", "CHUNK_OVERLAP=200".

Pure dense (embedding) retrieval performs poorly on exact-match queries because semantic similarity is a poor proxy for lexical overlap: two chunks may be semantically close but one contains the exact error code and the other does not. Dense retrieval ranks both similarly.

Conversely, pure BM25 keyword retrieval fails on paraphrase queries and conceptual questions: "how does the system handle unreachable nodes?" will not match a chunk containing "pod eviction during node failure" if the user's exact words do not appear.

The retrieval quality directly determines RAGAS faithfulness and context precision scores — the primary quality gates for this system.

## Decision
Implement hybrid retrieval that combines:
1. **Dense search**: Qdrant cosine-similarity search over text-embedding-3-large vectors, top-k results
2. **Sparse search**: BM25 keyword match (rank-bm25 library) over the same corpus, top-k results
3. **Fusion**: Reciprocal Rank Fusion (RRF) merges both ranked lists into a single ranked list
4. **Re-ranking**: Cross-encoder (cross-encoder/ms-marco-MiniLM-L-6-v2, ~85MB HuggingFace model) re-scores the merged top-k for final precision

Metadata filtering (filename, file_type, tags) is applied at the Qdrant query level before fusion, not as a routing decision.

## Alternatives Considered

**Dense-only retrieval**: Simpler, one index to maintain. Rejected because it provably loses recall on exact-match queries over technical content. RAGAS context recall would be lower on the golden dataset.

**BM25-only retrieval**: No embedding infrastructure needed. Rejected because it fails on semantic paraphrase queries, which are the majority of natural-language knowledge base questions.

**Separate domain routing**: Route queries to different retrievers based on detected domain (e.g., "networking" queries go to a networking document index). Rejected explicitly by CLAUDE.md architecture rules: "No hard-coded domain routing." Domain-specific routing creates brittle coupling and limits cross-domain retrieval. Metadata filtering achieves scoping without routing.

**Qdrant native sparse vectors (SPLADE)**: Use Qdrant's built-in sparse vector support instead of an in-memory BM25 index. Not selected for Phase 1 because it requires generating sparse vectors at ingestion time (additional embedding step), whereas rank-bm25 computes BM25 scores from the raw text at query time. Migration path: replace the in-memory BM25 index with Qdrant sparse vectors in Phase 3.

**No re-ranker**: Skip the cross-encoder step. Rejected because re-ranking has been shown to significantly improve precision at top-3, which is the citation count that matters for the UI. The ~100–200ms latency cost is acceptable within the 8s P95 budget.

## Consequences

**Positive:**
- Dense + BM25 fusion captures both semantic similarity and lexical overlap, improving recall on the golden dataset
- RRF is parameter-free in its basic form (k=60 constant), reducing tuning complexity
- Cross-encoder re-ranking improves precision at top-3 without requiring GPU (CPU inference, ~85MB model)
- Metadata filtering at the Qdrant level keeps retrieval domain-agnostic while still supporting scoped queries

**Negative:**
- Two retrieval indices must be maintained in sync: Qdrant vectors and an in-memory BM25 index (rank-bm25). If the BM25 index is not rebuilt after ingestion, results will diverge.
- BM25 index is in-memory: must be serialized to disk and reloaded on service restart. Adds a startup step and a persistence concern.
- Re-ranker adds ~100–200ms latency on CPU per query. Acceptable for MVP; revisit if P95 latency exceeds budget.
- Cross-encoder model (~85MB) is downloaded from HuggingFace on first run. Docker image size increases if included in the build layer.
