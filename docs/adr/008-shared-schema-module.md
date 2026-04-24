# ADR-008: Shared Schema Module for Cross-Layer Types

## Status
Accepted

## Context
`generation/models.py` and `api/schemas.py` each define identical Pydantic models for the same domain concepts:

| `generation/models.py` | `api/schemas.py` |
|------------------------|------------------|
| `Citation`             | `CitationItem`   |
| `GenerationResult`     | `QueryResponse`  |

The duplication means any field addition or rename requires edits in two files, and the divergent names (`Citation` vs `CitationItem`) imply a distinction that does not exist in the domain. The duplication was introduced because the generation and API layers were built in separate tasks; it was not a deliberate design choice.

This problem surfaced during the ADR-007 LCEL migration, which requires `generation/chain.py` to return `GenerationResult` objects that are then serialised by the API layer. The two representations must be reconciled before that migration can proceed cleanly.

## Decision
Create `backend/src/schemas/generation.py` as the single canonical location for types shared between the generation domain layer and the API presentation layer.

**New module layout:**
```
backend/src/schemas/__init__.py        # empty, marks the package
backend/src/schemas/generation.py     # Citation, GenerationResult
```

**`backend/src/schemas/generation.py` defines:**
- `Citation` — canonical name for a single cited source chunk. Fields: `chunk_id: str`, `filename: str`, `source_path: str`, `page_number: int`.
- `GenerationResult` — canonical name for the full output of the generation pipeline. Fields: `query: str`, `answer: str`, `citations: list[Citation]`, `confidence: float`.

**Import contracts after migration:**
- `backend/src/generation/chain.py` imports `Citation` and `GenerationResult` from `src.schemas.generation`.
- `backend/src/api/schemas.py` imports `Citation` and `GenerationResult` from `src.schemas.generation`. `CitationItem` becomes a type alias `CitationItem = Citation` to preserve backward compatibility with any existing serialised API responses or tests that reference the name. `QueryResponse` is redefined as a thin subclass or alias of `GenerationResult` if the fields are identical, or imports it directly.
- `backend/src/generation/models.py` is deleted once all imports are migrated and tests are green.

**The `AgentState` contract** (defined in `architecture-rules.md`) specifies `citations: list[Citation]`. After this migration, that field imports `Citation` from `src.schemas.generation`, which is the correct and only definition.

## Alternatives Considered

**Option A — `api/schemas.py` imports from `generation/models.py`:** Makes the API layer (presentation) dependent on an internal generation module (domain). This is an unconventional and fragile dependency direction — a rename in the generation module breaks the API contract. Rejected.

**Option B — `generation/chain.py` imports from `api/schemas.py`:** Makes the domain layer dependent on the presentation layer. This is a layering violation that would prevent the generation module from being used outside an HTTP context (e.g., in CLI evaluation scripts, RAGAS evaluation, or LangGraph agent nodes in Phase 2). Rejected.

**Option C — shared `src/schemas/` neutral module:** No circular dependency. Neither `src/api/` nor `src/generation/` depends on the other; both depend on `src/schemas/`, which has no upward dependency. This is the standard resolution for cross-layer type sharing. Accepted.

**Keeping the duplication with a comment:** Rejected. Duplicate definitions diverge over time. The `CitationItem`/`Citation` name split already demonstrates this — the `Item` suffix was applied to a domain concept without reason. A comment does not enforce consistency; a single import does.

## Consequences

**Positive:**
- One definition of `Citation` and `GenerationResult` in the entire codebase; field changes are made in one file and propagate to both layers automatically
- `src/schemas/` carries no imports from `src/api/` or `src/generation/`, so it is safe to import from Phase 2 LangGraph agent node files without introducing circular imports
- `AgentState.citations: list[Citation]` (Phase 2) and the API `QueryResponse.citations` field reference the same type, eliminating any conversion step between the agent layer and the API response serialiser
- `generation/models.py` is deleted, reducing the module count and eliminating a file that existed only due to layering ambiguity

**Negative:**
- One-time migration: `chain.py`, `api/schemas.py`, and their unit tests must update their import paths. The change is mechanical and contained within `backend/src/`.
- `CitationItem` must be kept as a type alias in `api/schemas.py` for one release cycle if external API clients reference it by name in their deserialisers; after that it can be removed.
