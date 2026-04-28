"""Retriever node — calls HybridRetriever or Tavily web fallback."""

import asyncio
import time
from typing import TYPE_CHECKING, Any, Literal, Protocol, cast, runtime_checkable

import structlog
from langchain_core.documents import Document

from src.graph.state import AgentState

if TYPE_CHECKING:
    from src.retrieval.models import RetrievalResult

log = structlog.get_logger(__name__)


@runtime_checkable
class RetrieverProtocol(Protocol):
    """Structural interface the retriever node depends on.

    Defined here so ``graph/nodes/`` never imports from ``retrieval/`` directly.
    """

    async def retrieve(
        self,
        query: str,
        k: int | None = None,
        filters: dict[str, str] | None = None,
        mode: Literal["dense", "hybrid"] = "hybrid",
    ) -> list[Any]:
        """Retrieve documents matching *query*."""
        ...


def _result_to_document(result: "RetrievalResult") -> Document:
    """Convert a RetrievalResult to a langchain_core Document."""
    metadata: dict[str, Any] = {
        "chunk_id": result.chunk_id,
        "score": result.score,
    }
    # ChunkMetadata is a TypedDict — access via dict key lookup.
    raw_meta = cast(dict[str, Any], result.metadata)
    source = raw_meta.get("source_path")
    if source is not None:
        metadata["source"] = source
    return Document(page_content=result.text, metadata=metadata)


async def retriever_node(
    state: AgentState,
    *,
    retriever: RetrieverProtocol | None = None,
    tavily_client: Any | None = None,
) -> dict[str, Any]:
    """Retrieve documents and return a partial AgentState update.

    Branches on ``state.retrieval_strategy``:
    - ``"dense"`` / ``"hybrid"`` → delegates to *retriever* (HybridRetriever).
    - ``"web"`` → calls the Tavily API via *tavily_client*; sets
      ``web_fallback_used = True``.

    On any retrieval error the node logs a warning and returns an empty
    ``retrieved_docs`` list — it never propagates exceptions.

    Args:
        state: Current AgentState snapshot.
        retriever: Injected HybridRetriever (must be provided for dense/hybrid
            strategies; may be ``None`` only when strategy is ``"web"``).
        tavily_client: Injected TavilyClient singleton (required for web
            strategy; constructed once in build_graph()).

    Returns:
        Partial state dict with ``retrieved_docs``, ``web_fallback_used``, and
        an appended ``steps_taken`` entry.
    """
    strategy: str = state["retrieval_strategy"]
    _rewritten: str | None = state["query_rewritten"]
    effective_query: str = _rewritten if _rewritten else state["query"]
    k: int | None = state["k"]
    filters: dict[str, str] | None = state["filters"]

    docs: list[Document] = []
    web_fallback_used = False
    t0 = time.monotonic()

    if strategy in ("dense", "hybrid"):
        if retriever is None:
            log.warning(
                "retriever_not_injected",
                strategy=strategy,
                query=effective_query,
            )
        else:
            try:
                results: list[Any] = await retriever.retrieve(
                    effective_query,
                    k=k,
                    filters=filters,
                    mode=cast(Literal["dense", "hybrid"], strategy),
                )
                docs = [_result_to_document(r) for r in results]
                log.info(
                    "retriever_hybrid_complete",
                    strategy=strategy,
                    doc_count=len(docs),
                    query_len=len(effective_query),
                )
            except Exception as exc:
                log.warning(
                    "retriever_hybrid_failed",
                    strategy=strategy,
                    error=str(exc),
                    query=effective_query,
                )
                docs = []

    elif strategy == "web":
        if tavily_client is None:
            log.warning("tavily_client_not_injected", query=effective_query)
        else:
            try:
                max_results = k if k is not None else 5
                response: dict[str, Any] = await asyncio.to_thread(
                    tavily_client.search,
                    query=effective_query,
                    max_results=max_results,
                )
                raw_results: list[dict[str, Any]] = response.get("results", [])
                docs = [
                    Document(
                        page_content=r["content"],
                        metadata={
                            "source": r["url"],
                            "title": r.get("title", ""),
                            "score": float(r.get("score", 0.0)),
                        },
                    )
                    for r in raw_results
                ]
                web_fallback_used = True
                log.info(
                    "retriever_web_complete", doc_count=len(docs), query_len=len(effective_query)
                )
            except Exception as exc:
                log.warning("retriever_web_failed", error=str(exc), query=effective_query)
                docs = []
                web_fallback_used = False
    else:
        log.warning(
            "retriever_unknown_strategy",
            strategy=strategy,
            query=effective_query,
        )

    duration_ms = int((time.monotonic() - t0) * 1000)
    step_label = f"retriever:{strategy}:{duration_ms}ms"

    return {
        "retrieved_docs": docs,
        "web_fallback_used": web_fallback_used,
        "steps_taken": [step_label],
    }
