"""POST /api/v1/query/agentic — agentic RAG query via SSE streaming.

Each intermediate node (router, grader, critic) emits an ``agent_step`` event.
The generator node emits ``token``, ``citations``, and ``done`` events.
"""

import json
import uuid
from collections.abc import AsyncGenerator

import structlog
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from langchain_core.runnables import RunnableConfig

from src.api.deps import CompiledGraphDep
from src.api.schemas.agentic import (
    AgentQueryRequest,
    AgentStepEvent,
    CriticStepPayload,
    GraderStepPayload,
    RouterStepPayload,
)

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


def _build_agent_step_event(
    node_name: str, state_update: dict[str, object]
) -> AgentStepEvent:
    """Construct an AgentStepEvent from a node name and its state delta."""
    steps: list[str] = state_update.get("steps_taken", [])  # type: ignore[assignment]
    duration_ms = _parse_duration_ms(steps[0]) if steps else 0
    if node_name == "router":
        return AgentStepEvent(
            node="router",
            payload=RouterStepPayload(
                query_type=state_update["query_type"],  # type: ignore[arg-type]
                strategy=state_update["retrieval_strategy"],  # type: ignore[arg-type]
                duration_ms=duration_ms,
            ),
        )
    if node_name == "grader":
        return AgentStepEvent(
            node="grader",
            payload=GraderStepPayload(
                scores=state_update.get("grader_scores", []),  # type: ignore[arg-type]
                web_fallback=state_update.get("all_below_threshold", False),  # type: ignore[arg-type]
                duration_ms=duration_ms,
            ),
        )
    # critic
    critic_score: float = state_update.get("critic_score") or 0.0  # type: ignore[assignment]
    return AgentStepEvent(
        node="critic",
        payload=CriticStepPayload(
            hallucination_risk=critic_score,
            reruns=state_update.get("retry_count", 0),  # type: ignore[arg-type]
            duration_ms=duration_ms,
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
        "session_id": session_id,
        "query": body.query,
        "filters": body.filters,
        "k": body.k,
        "retry_count": 0,
    }
    config: RunnableConfig = {"configurable": {"thread_id": session_id}}

    async def _stream() -> AsyncGenerator[str, None]:
        _grader_doc_count: int = 0
        try:
            async for chunk in compiled_graph.astream(
                initial_state,
                config=config,
                stream_mode="updates",
            ):
                for node_name, state_update in chunk.items():
                    if node_name in ("router", "grader", "critic"):
                        if node_name == "grader":
                            _grader_doc_count = len(
                                state_update.get("graded_docs", [])
                            )
                        event = _build_agent_step_event(node_name, state_update)
                        yield f"data: {event.model_dump_json()}\n\n"

                    elif node_name == "generator":
                        answer: str = state_update.get("answer") or ""
                        for word in answer.split(" "):
                            if word:
                                yield f"data: {json.dumps({'type': 'token', 'content': word + ' '})}\n\n"

                        citations = state_update.get("citations", [])
                        # Citations may be Citation objects; serialise each with model_dump if available
                        serialised_citations = [
                            c.model_dump() if hasattr(c, "model_dump") else c
                            for c in citations
                        ]
                        confidence: float | None = state_update.get("confidence")
                        chunks_retrieved: int = _grader_doc_count
                        yield (
                            f"data: {json.dumps({'type': 'citations', 'citations': serialised_citations, 'confidence': confidence, 'chunks_retrieved': chunks_retrieved})}\n\n"
                        )

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
