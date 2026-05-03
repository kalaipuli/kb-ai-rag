"""POST /api/v1/query/agentic — agentic RAG query via SSE streaming.

Each node (router, retriever, grader, generator, critic) emits an ``agent_step``
event. The generator node additionally emits ``token`` and ``citations`` events.
A ``done`` event closes the stream.
"""

import json
import uuid
from collections.abc import AsyncGenerator
from typing import Literal

import structlog
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from langchain_core.runnables import RunnableConfig

from src.api.deps import CompiledGraphDep
from src.api.schemas.agentic import (
    AgentQueryRequest,
    AgentStepEvent,
    CriticStepPayload,
    GeneratorStepPayload,
    GraderStepPayload,
    RetrieverStepPayload,
    RouterStepPayload,
)
from src.config import get_settings
from src.graph.node_names import CRITIC, GENERATOR, GRADER, RETRIEVER, ROUTER

logger = structlog.get_logger(__name__)

router = APIRouter()


def _parse_duration_ms(step: str) -> int:
    """Parse duration_ms from a steps_taken entry like 'router:factual:hybrid:45ms'.

    Returns 0 if the entry is malformed rather than raising.
    """
    try:
        raw = step.rsplit(":", 1)[-1]
        return int(raw.removesuffix("ms"))
    except (ValueError, IndexError):
        return 0


def _parse_retriever_strategy(step: str) -> Literal["dense", "hybrid", "web"]:
    """Parse retrieval strategy from a steps_taken entry like 'retriever:hybrid:156ms'.

    Position index 1 in the colon-split holds the strategy token.
    Returns ``"hybrid"`` as a safe default when the entry is malformed.
    """
    try:
        parts = step.split(":")
        token = parts[1]
        if token in ("dense", "hybrid", "web"):
            return token  # type: ignore[return-value]
    except IndexError:
        pass
    return "hybrid"


def _build_agent_step_event(
    node_name: str,
    state_update: dict[str, object],
    run: int,
    docs_used: int = 0,
) -> AgentStepEvent:
    """Construct an AgentStepEvent from a node name, its state delta, and run counter."""
    steps: list[str] = state_update.get("steps_taken", [])  # type: ignore[assignment]
    duration_ms = _parse_duration_ms(steps[0]) if steps else 0
    settings = get_settings()

    if node_name == ROUTER:
        query_type: str = str(state_update.get("query_type", "factual"))
        query_rewritten: str | None = state_update.get("query_rewritten")  # type: ignore[assignment]
        rewrite_method: Literal["none", "hyde", "stepback"] = "none"
        if query_rewritten is not None:
            if query_type == "analytical":
                rewrite_method = "hyde"
            elif query_type == "multi_hop":
                rewrite_method = "stepback"
        return AgentStepEvent(
            node=ROUTER,
            run=run,
            payload=RouterStepPayload(
                query_type=state_update["query_type"],  # type: ignore[arg-type]
                strategy=state_update["retrieval_strategy"],  # type: ignore[arg-type]
                duration_ms=duration_ms,
                query_rewritten=query_rewritten,
                rewrite_method=rewrite_method,
            ),
        )
    if node_name == RETRIEVER:
        strategy = _parse_retriever_strategy(steps[0]) if steps else "hybrid"
        retrieved: list[object] = state_update.get("retrieved_docs", [])  # type: ignore[assignment]
        return AgentStepEvent(
            node=RETRIEVER,
            run=run,
            payload=RetrieverStepPayload(
                strategy=strategy,
                docs_retrieved=len(retrieved),
                duration_ms=duration_ms,
            ),
        )
    if node_name == GRADER:
        all_below: bool = bool(state_update.get("all_below_threshold", False))
        _raw_retry: object = state_update.get("retry_count") or 0
        retry_count: int = int(_raw_retry)  # type: ignore[call-overload]  # object is int at runtime
        grader_decision: Literal["proceed", "retry", "escalate_web"]
        if state_update.get("retrieval_strategy") == "web":
            grader_decision = "escalate_web"
        elif all_below and retry_count < settings.graph_max_retries:
            grader_decision = "retry"
        else:
            grader_decision = "proceed"
        return AgentStepEvent(
            node=GRADER,
            run=run,
            payload=GraderStepPayload(
                scores_all=state_update.get("grader_scores", []),  # type: ignore[arg-type]
                passed_count=len(state_update.get("graded_docs", [])),  # type: ignore[arg-type]
                threshold=settings.grader_threshold,
                all_below_threshold=all_below,
                duration_ms=duration_ms,
                decision=grader_decision,
            ),
        )
    if node_name == GENERATOR:
        raw_confidence: float = state_update.get("confidence") or 0.0  # type: ignore[assignment]
        confidence = max(0.0, min(1.0, float(raw_confidence)))
        return AgentStepEvent(
            node=GENERATOR,
            run=run,
            payload=GeneratorStepPayload(
                docs_used=docs_used,
                confidence=confidence,
                duration_ms=duration_ms,
            ),
        )
    # critic
    critic_score: float = state_update.get("critic_score") or 0.0  # type: ignore[assignment]
    critic_verdict: Literal["accept", "rerun"] = (
        "rerun" if critic_score > settings.critic_threshold else "accept"
    )
    return AgentStepEvent(
        node=CRITIC,
        run=run,
        payload=CriticStepPayload(
            hallucination_risk=critic_score,
            reruns=state_update.get("retry_count", 0),  # type: ignore[arg-type]
            duration_ms=duration_ms,
            verdict=critic_verdict,
        ),
    )


@router.post("/query/agentic")
async def query_agentic_endpoint(
    body: AgentQueryRequest,
    compiled_graph: CompiledGraphDep,
    request: Request,
) -> StreamingResponse:
    """Stream agentic RAG results over SSE.

    Emits one ``agent_step`` event per intermediate node, then ``token``,
    ``citations``, and ``done`` events from the generator node.
    """
    session_id = request.headers.get("X-Session-ID") or str(uuid.uuid4())
    logger.info(
        "agentic_query_received",
        query_len=len(body.query),
        session_id=session_id,
    )

    initial_state: dict[str, object] = {
        # Input fields
        "session_id": session_id,
        "query": body.query,
        "filters": body.filters,
        "k": body.k,
        # Router outputs
        "query_type": "factual",
        "retrieval_strategy": "hybrid",
        "query_rewritten": None,
        # Retriever outputs
        "retrieved_docs": [],
        "web_fallback_used": False,
        # Grader outputs
        "grader_scores": [],
        "graded_docs": [],
        "all_below_threshold": False,
        "retry_count": 0,
        # Generator outputs
        "answer": None,
        "citations": [],
        "confidence": None,
        # Critic outputs
        "critic_score": None,
        # Conversation / observability
        "messages": [],
        "steps_taken": [],
    }
    config: RunnableConfig = {"configurable": {"thread_id": session_id}}

    async def _stream() -> AsyncGenerator[str, None]:
        _grader_doc_count: int = 0
        _context_texts: list[str] = []
        _run_count: dict[str, int] = {}

        try:
            async for chunk in compiled_graph.astream(
                initial_state,
                config=config,
                stream_mode="updates",
            ):
                for node_name, state_update in chunk.items():
                    _run_count[node_name] = _run_count.get(node_name, 0) + 1
                    run = _run_count[node_name]

                    if node_name == ROUTER:
                        event = _build_agent_step_event(node_name, state_update, run=run)
                        yield f"data: {event.model_dump_json()}\n\n"

                    elif node_name == RETRIEVER:
                        event = _build_agent_step_event(node_name, state_update, run=run)
                        yield f"data: {event.model_dump_json()}\n\n"
                        # Update context texts after emitting event; preserve existing guard.
                        retrieved = state_update.get("retrieved_docs", [])
                        if retrieved and not _context_texts:
                            _context_texts = [
                                doc.page_content if hasattr(doc, "page_content") else ""
                                for doc in retrieved
                                if doc
                            ]

                    elif node_name == GRADER:
                        graded = state_update.get("graded_docs", [])
                        _grader_doc_count = len(graded)
                        _context_texts = [
                            doc.page_content if hasattr(doc, "page_content") else ""
                            for doc in graded
                            if doc
                        ]
                        event = _build_agent_step_event(node_name, state_update, run=run)
                        yield f"data: {event.model_dump_json()}\n\n"

                    elif node_name == GENERATOR:
                        answer: str = state_update.get("answer") or ""
                        for word in answer.split(" "):
                            if word:
                                yield f"data: {json.dumps({'type': 'token', 'content': word + ' '})}\n\n"

                        gen_event = _build_agent_step_event(
                            node_name,
                            state_update,
                            run=run,
                            docs_used=_grader_doc_count,
                        )
                        yield f"data: {gen_event.model_dump_json()}\n\n"

                        citations = state_update.get("citations", [])
                        serialised_citations = [
                            c.model_dump() if hasattr(c, "model_dump") else c for c in citations
                        ]
                        confidence: object = state_update.get("confidence")
                        chunks_retrieved: int = _grader_doc_count
                        yield (
                            f"data: {json.dumps({'type': 'citations', 'citations': serialised_citations, 'confidence': confidence, 'chunks_retrieved': chunks_retrieved, 'retrieved_contexts': _context_texts})}\n\n"
                        )

                    elif node_name == CRITIC:
                        event = _build_agent_step_event(node_name, state_update, run=run)
                        yield f"data: {event.model_dump_json()}\n\n"

        except Exception as exc:
            logger.error(
                "agentic_stream_error",
                error=str(exc),
                session_id=session_id,
                query_len=len(body.query),
            )

        # Always emit done — even after a mid-stream exception — so the client can close.
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(_stream(), media_type="text/event-stream")
