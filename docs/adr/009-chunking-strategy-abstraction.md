# ADR-009: Chunking Strategy Abstraction and Token-Aware Splitting

**Status:** Accepted  
**Date:** 2026-04-26  
**Deciders:** Architect, Backend Developer  
**Supersedes:** None  
**Related:** ADR-003 (hybrid retrieval), ADR-008 (shared schema module)

---

## Context

Phase 1 hard-codes `RecursiveCharacterTextSplitter` with a character-based length function (`len`) and fixed `chunk_size=1000 / chunk_overlap=200` in `DocumentSplitter`. This has two problems:

1. **Character count ≠ token count.** The LLM context window is measured in tokens. A 1000-char chunk can be 150–350 tokens depending on vocabulary density, making the "size" parameter semantically meaningless relative to the model's actual context budget.
2. **No strategy flexibility.** Every document type — dense technical manuals, FAQ lists, policy documents — is split identically. Semantic boundaries are ignored, causing chunks to straddle topic transitions and degrading context recall.

The RAGAS baseline (faithfulness 0.9153, context recall 0.9542) was measured against this fixed strategy. To prove retrieval quality can be improved further, and to enable future experimentation, chunking strategy must be configurable without code changes.

---

## Decision

### 1. Introduce a `SplitterFactory` with a `ChunkStrategy` enum

A new module `backend/src/ingestion/splitter_factory.py` provides:

```python
class ChunkStrategy(str, Enum):
    recursive_character = "recursive_character"
    sentence_window     = "sentence_window"
    semantic            = "semantic"

class SplitterFactory:
    @staticmethod
    def build(settings: Settings, embedder: Embedder | None = None) -> TextSplitter:
        ...
```

`DocumentSplitter.__init__` calls `SplitterFactory.build(settings, embedder)` instead of hardcoding `RecursiveCharacterTextSplitter`. The active strategy is controlled by `CHUNK_STRATEGY` in `.env`.

### 2. Token-aware length function for all strategies

`tiktoken` (pinned `^0.8`) is added as an explicit dependency. The `length_function` for any character-based splitter is replaced with a tiktoken token counter using the model specified by `CHUNK_TOKENIZER_MODEL` (default `cl100k_base`, matching both `text-embedding-ada-002` and `text-embedding-3-large`). This ensures `chunk_size` is measured in tokens, not characters.

### 3. Strategies shipped in Phase 1g

| Strategy | Library | Phase |
|---|---|---|
| `recursive_character` | `langchain-text-splitters` (already present) | 1g |
| `sentence_window` | `nltk` sentence tokenizer, grouped into N-sentence windows | 1g |
| `semantic` | `langchain-experimental` `SemanticChunker` | 1g **if** dry-run passes (see risk below) |

**`langchain-experimental` gate:** Before implementation of the `semantic` strategy begins, the implementing agent must run:

```bash
poetry add langchain-experimental --dry-run
```

If this produces a `langchain-core` version conflict with the existing `langchain-openai ^0.2` pin, the `semantic` strategy is deferred to Phase 2 and `ChunkStrategy.semantic` is kept in the enum but raises `ConfigurationError` at startup with the message `"semantic strategy requires langchain-experimental; see ADR-009"`.

**Dry-run result (2026-04-26):** CONFLICT. `langchain-experimental ^0.4.1` requires `langchain-text-splitters >=1.0.0`, but the project pins `langchain-text-splitters ^0.3`. The `semantic` strategy is **deferred to Phase 2**. `ChunkStrategy.semantic` is present in the enum but raises `ConfigurationError` with the message above.

### 4. Embedder injection for the `semantic` strategy

`SemanticChunker` requires an embeddings client at construction time. The implementing agent must **not** create a second `AzureOpenAIEmbeddings` instance inside the factory. The `Embedder` singleton (already created in the lifespan block) must be passed into `run_pipeline` and from there into `SplitterFactory.build()`.

Changes required:

- `backend/src/api/main.py`: add `app.state.embedder = embedder` to the lifespan block (alongside `app.state.generation_chain`).
- `backend/src/api/deps.py`: add `get_embedder` function and `EmbedderDep = Annotated[Embedder, Depends(get_embedder)]`.
- `backend/src/api/routes/ingest.py`: accept `EmbedderDep` and pass it to `run_pipeline`.
- `backend/src/ingestion/pipeline.py`: add `embedder: Embedder | None = None` parameter to `run_pipeline`; forward to `SplitterFactory.build`.

If `semantic` strategy is selected and `embedder` is `None`, the factory raises `ConfigurationError` at pipeline startup — not silently at first chunk.

### 5. AnswerCorrectness added as 5th RAGAS metric

`AnswerCorrectness` is added to the `RagasEvaluator` alongside the existing four metrics. This makes each evaluation run issue **5× LLM calls per sample** (one per metric) rather than 4×. For a 20-question golden dataset this is ~100 LLM calls total per run — acceptable at current Azure quota, but worth noting for future dataset scaling.

### 6. Evaluation baseline path moves to Settings

The evaluation runner writes `eval_baseline.json` to `Settings.eval_baseline_path` (default: `data/eval_baseline.json`). This keeps the file in the existing runtime data directory (alongside `bm25_index.pkl`), out of the source tree. `data/eval_baseline.json` is added to `.gitignore`.

---

## Consequences

**Positive:**
- Chunk size is now meaningful relative to the LLM context window.
- Strategy can be changed per deployment via environment variable — no code change required to compare strategies.
- RAGAS can be re-run against different strategies, producing evidence of improvement.
- `Embedder` singleton ownership remains with the lifespan block — no hidden client duplication.

**Negative:**
- Tiktoken adds a dependency and a marginal import-time cost.
- NLTK requires a data download (`nltk.download("punkt_tab")`) — must be added to the Dockerfile and documented in `README`.
- If `langchain-experimental` conflicts, the `semantic` strategy cannot ship in Phase 1g and must be deferred.
- `run_pipeline` signature gains an optional parameter, requiring the ingest route handler update.

---

## Rejected Alternatives

**Hardcode multiple splitter classes without a factory:** Would require touching `DocumentSplitter` and `pipeline.py` for every new strategy. Rejected in favour of the factory/enum pattern which isolates strategy logic and makes the extension point explicit.

**Create a separate embedder inside the factory for `semantic` strategy:** Would violate the lifespan singleton rule, duplicate rate-limit state, and bypass the semaphore/inter-batch-delay logic in `Embedder`. Rejected.

**UI-driven runtime strategy switching:** The strategy directly controls how documents are indexed. Changing it mid-session would invalidate existing indexed chunks. Strategy is correctly an ingest-time configuration, not a query-time one. Rejected.
