"""Integration smoke tests for the compiled LangGraph workflow.

Invokes the compiled graph end-to-end with real node implementations,
real edge routing functions, and mocked LLM/retriever calls.
No real Azure or Tavily calls are made.

Test cases:
1. Happy path: factual query; grader scores >= 0.5; critic_score <= 0.7 → END in one pass
2. CRAG path: all grader scores < 0.5 on first pass → re-routes to retriever → END second pass
3. Self-RAG path: critic_score > 0.7 on first pass → re-routes to retriever → END second pass
4. Max retry guard: both grader and critic would fire indefinitely → terminates after MAX_RETRIES

Patch strategy:
- `src.graph.builder.AzureChatOpenAI` — intercepts both llm and llm_4o construction;
  a single mock instance is returned whose `with_structured_output` dispatch controls all nodes.
- `src.graph.builder.retriever_node` — intercepts the retriever closure in build_graph()
  so each test controls retrieved_docs and call counts independently.
- `src.graph.edges.get_settings` and `src.graph.nodes.grader.get_settings` — patched with
  graph_max_retries=2 in re-routing tests so that grader's increment of retry_count (0→1)
  still leaves budget for one CRAG/Self-RAG re-route (1 < 2 = True).
  The max-retry-guard test uses graph_max_retries=1 (default).
"""

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.documents import Document

from src.graph.builder import build_graph
from src.graph.nodes.critic import _CriticOutput
from src.graph.nodes.generator import _GeneratorOutput
from src.graph.nodes.grader import _GradeDoc
from src.graph.nodes.router import (
    _RouterOutput,  # noqa: F401  # imported for schema name dispatch in _make_llm_mock
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_doc(content: str = "Some relevant content.") -> Document:
    return Document(
        page_content=content,
        metadata={"chunk_id": "c1", "source": "/data/doc.pdf"},
    )


def _mock_settings(tmp_path: Path) -> Any:
    settings = MagicMock()
    settings.sqlite_checkpointer_path = str(tmp_path / "integration_test.sqlite")
    settings.azure_openai_endpoint = "https://fake-endpoint.openai.azure.com/"
    settings.azure_openai_api_key.get_secret_value.return_value = "fake-api-key"
    settings.azure_openai_api_version = "2024-08-01-preview"
    settings.azure_chat_deployment = "gpt-4o"
    return settings


def _initial_state(query: str = "What is the capital of France?") -> dict[str, Any]:
    return {
        "session_id": "integration-test",
        "query": query,
        "filters": None,
        "k": None,
        "query_type": "factual",
        "retrieval_strategy": "hybrid",
        "query_rewritten": None,
        "retrieved_docs": [],
        "web_fallback_used": False,
        "grader_scores": [],
        "graded_docs": [],
        "all_below_threshold": False,
        "retry_count": 0,
        "answer": None,
        "citations": [],
        "confidence": None,
        "critic_score": None,
        "messages": [],
        "steps_taken": [],
    }


def _make_llm_mock(
    *,
    router_output: _RouterOutput,
    grader_outputs: list[list[_GradeDoc]],
    gen_output: _GeneratorOutput,
    critic_outputs: list[_CriticOutput],
) -> MagicMock:
    """Build a mock LLM whose with_structured_output dispatch drives all nodes.

    grader_outputs is a list of batch results per grader call (one list per call).
    critic_outputs is a list of results per critic ainvoke call (one per call).
    """
    router_chain = MagicMock()
    router_chain.ainvoke = AsyncMock(return_value=router_output)

    grader_call_index = [0]

    def _grader_batch(messages: Any) -> list[_GradeDoc]:
        idx = grader_call_index[0]
        grader_call_index[0] += 1
        if idx < len(grader_outputs):
            return grader_outputs[idx]
        # Fallback to last available
        return grader_outputs[-1]

    grader_chain = MagicMock()
    grader_chain.batch = MagicMock(side_effect=_grader_batch)

    gen_chain = MagicMock()
    gen_chain.ainvoke = AsyncMock(return_value=gen_output)

    critic_call_index = [0]

    async def _critic_ainvoke(messages: Any) -> _CriticOutput:
        idx = critic_call_index[0]
        critic_call_index[0] += 1
        if idx < len(critic_outputs):
            return critic_outputs[idx]
        return critic_outputs[-1]

    critic_chain = MagicMock()
    critic_chain.ainvoke = AsyncMock(side_effect=_critic_ainvoke)

    schema_map: dict[str, MagicMock] = {
        "_RouterOutput": router_chain,
        "_GradeDoc": grader_chain,
        "_GeneratorOutput": gen_chain,
        "_CriticOutput": critic_chain,
    }

    def _with_structured_output(schema: Any) -> MagicMock:
        return schema_map.get(schema.__name__, MagicMock())

    llm_mock = MagicMock()
    llm_mock.with_structured_output.side_effect = _with_structured_output
    return llm_mock


async def _collect_terminal_state(compiled: Any, initial: dict[str, Any]) -> dict[str, Any]:
    """Stream the graph and return the merged terminal state."""
    config = {"configurable": {"thread_id": initial["session_id"]}}
    terminal: dict[str, Any] = dict(initial)
    async for update in compiled.astream(initial, config=config, stream_mode="updates"):
        for node_update in update.values():
            if isinstance(node_update, dict):
                for k, v in node_update.items():
                    # steps_taken and messages accumulate (reducer fields).
                    # retrieved_docs uses plain replacement semantics (ADR-011).
                    if k in ("steps_taken", "messages") and isinstance(v, list):
                        existing = terminal.get(k, [])
                        terminal[k] = (existing if isinstance(existing, list) else []) + v
                    else:
                        terminal[k] = v
    return terminal


def _make_retriever_node_mock(
    doc: Document,
) -> tuple[AsyncMock, list[int]]:
    """Return (mock_fn, call_counter_list) so tests can assert call count.

    The builder closure calls retriever_node(state, retriever=retriever), so
    the mock must accept **kwargs to absorb the injected retriever kwarg.
    """
    call_count: list[int] = [0]

    async def _fn(state: Any, **kwargs: Any) -> dict[str, Any]:
        call_count[0] += 1
        return {
            "retrieved_docs": [doc],
            "web_fallback_used": False,
            "steps_taken": [f"retriever:hybrid:pass{call_count[0]}:1ms"],
        }

    return AsyncMock(side_effect=_fn), call_count


# ---------------------------------------------------------------------------
# Test 1: Happy path — one pass, reaches END
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_happy_path_reaches_end_in_one_pass(tmp_path: Path) -> None:
    settings = _mock_settings(tmp_path)
    doc = _make_doc()
    retriever_mock, call_count = _make_retriever_node_mock(doc)

    llm_mock = _make_llm_mock(
        router_output=_RouterOutput(
            query_type="factual", retrieval_strategy="hybrid", reasoning="ok"
        ),
        grader_outputs=[[_GradeDoc(score=0.9, reasoning="relevant")]],
        gen_output=_GeneratorOutput(answer="Paris.", confidence=0.95, reasoning="clear"),
        critic_outputs=[
            _CriticOutput(hallucination_risk=0.1, unsupported_claims=[], reasoning="grounded")
        ],
    )

    with (
        patch("src.graph.builder.AzureChatOpenAI", return_value=llm_mock),
        patch("src.graph.builder.retriever_node", retriever_mock),
    ):
        compiled = await build_graph(settings=settings, retriever=MagicMock())
        terminal = await _collect_terminal_state(compiled, _initial_state())

    assert terminal["answer"] == "Paris."
    assert terminal["critic_score"] == pytest.approx(0.1)
    assert terminal["all_below_threshold"] is False
    # Only one retriever pass needed
    assert call_count[0] == 1


# ---------------------------------------------------------------------------
# Test 2: CRAG path — all grader scores < 0.5 → re-routes to retriever
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_crag_path_reroutes_to_retriever(tmp_path: Path) -> None:
    # MAX_RETRIES patched to 2 so grader increment (0→1) still leaves budget for one re-route
    settings = _mock_settings(tmp_path)
    doc = _make_doc()
    retriever_mock, call_count = _make_retriever_node_mock(doc)

    llm_mock = _make_llm_mock(
        router_output=_RouterOutput(
            query_type="factual", retrieval_strategy="hybrid", reasoning="ok"
        ),
        # First grader call: 1 doc, all below threshold → CRAG re-route
        # Second grader call: plain replacement — retrieved_docs has exactly 1 doc (ADR-011)
        grader_outputs=[
            [_GradeDoc(score=0.1, reasoning="irrelevant")],
            [_GradeDoc(score=0.8, reasoning="now relevant")],
        ],
        gen_output=_GeneratorOutput(answer="Paris.", confidence=0.9, reasoning="ok"),
        critic_outputs=[
            _CriticOutput(hallucination_risk=0.2, unsupported_claims=[], reasoning="grounded")
        ],
    )

    edges_settings = MagicMock()
    edges_settings.graph_max_retries = 2
    edges_settings.grader_threshold = 0.5
    edges_settings.critic_threshold = 0.7
    edges_settings.grader_batch_size = 10

    with (
        patch("src.graph.builder.AzureChatOpenAI", return_value=llm_mock),
        patch("src.graph.builder.retriever_node", retriever_mock),
        patch("src.graph.edges.get_settings", return_value=edges_settings),
        patch("src.graph.nodes.grader.get_settings", return_value=edges_settings),
    ):
        compiled = await build_graph(settings=settings, retriever=MagicMock())
        terminal = await _collect_terminal_state(compiled, _initial_state())

    # Retriever called twice: initial + CRAG re-route
    assert call_count[0] >= 2
    assert terminal["answer"] == "Paris."


# ---------------------------------------------------------------------------
# Test 3: Self-RAG path — critic_score > 0.7 → re-routes to retriever
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_self_rag_path_reroutes_after_critic(tmp_path: Path) -> None:
    # MAX_RETRIES patched to 2 so grader increment (0→1) still leaves budget for critic re-route
    settings = _mock_settings(tmp_path)
    doc = _make_doc()
    retriever_mock, call_count = _make_retriever_node_mock(doc)

    llm_mock = _make_llm_mock(
        router_output=_RouterOutput(
            query_type="factual", retrieval_strategy="hybrid", reasoning="ok"
        ),
        # First grader call: 1 doc above threshold → generator → critic fires → re-route
        # Second grader call: plain replacement — retrieved_docs has exactly 1 doc (ADR-011)
        grader_outputs=[
            [_GradeDoc(score=0.8, reasoning="relevant")],
            [_GradeDoc(score=0.8, reasoning="still relevant")],
        ],
        gen_output=_GeneratorOutput(answer="Some answer.", confidence=0.7, reasoning="ok"),
        critic_outputs=[
            # First critic: high risk → Self-RAG re-route (retry_count=1 < MAX_RETRIES=2)
            _CriticOutput(
                hallucination_risk=0.85,
                unsupported_claims=["unsupported claim"],
                reasoning="hallucination detected",
            ),
            # Second critic: low risk → end
            _CriticOutput(hallucination_risk=0.15, unsupported_claims=[], reasoning="grounded"),
        ],
    )

    edges_settings = MagicMock()
    edges_settings.graph_max_retries = 2
    edges_settings.grader_threshold = 0.5
    edges_settings.critic_threshold = 0.7
    edges_settings.grader_batch_size = 10

    with (
        patch("src.graph.builder.AzureChatOpenAI", return_value=llm_mock),
        patch("src.graph.builder.retriever_node", retriever_mock),
        patch("src.graph.edges.get_settings", return_value=edges_settings),
        patch("src.graph.nodes.grader.get_settings", return_value=edges_settings),
    ):
        compiled = await build_graph(settings=settings, retriever=MagicMock())
        terminal = await _collect_terminal_state(compiled, _initial_state())

    # Retriever called at least twice: initial + Self-RAG re-route
    assert call_count[0] >= 2
    # Graph reached end with an answer
    assert terminal["answer"] is not None


# ---------------------------------------------------------------------------
# Test 4: Max retry guard — graph terminates after MAX_RETRIES=1
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_max_retry_guard_terminates(tmp_path: Path) -> None:
    """Graph must terminate even when grader and critic would loop indefinitely."""
    settings = _mock_settings(tmp_path)
    doc = _make_doc()
    retriever_mock, call_count = _make_retriever_node_mock(doc)

    llm_mock = _make_llm_mock(
        router_output=_RouterOutput(
            query_type="factual", retrieval_strategy="hybrid", reasoning="ok"
        ),
        # Grader always below threshold
        grader_outputs=[[_GradeDoc(score=0.0, reasoning="irrelevant")]],
        gen_output=_GeneratorOutput(answer="Fallback answer.", confidence=0.3, reasoning="low"),
        # Critic always high risk
        critic_outputs=[
            _CriticOutput(
                hallucination_risk=0.99,
                unsupported_claims=["everything"],
                reasoning="all hallucinated",
            )
        ],
    )

    with (
        patch("src.graph.builder.AzureChatOpenAI", return_value=llm_mock),
        patch("src.graph.builder.retriever_node", retriever_mock),
    ):
        compiled = await build_graph(settings=settings, retriever=MagicMock())
        terminal = await _collect_terminal_state(compiled, _initial_state())

    # Graph terminated — answer must be set
    assert terminal["answer"] is not None
    # Retriever not called more than graph_max_retries + 1 times
    # (1 initial + at most graph_max_retries=1 re-routes, the default)
    assert call_count[0] <= 2


# ---------------------------------------------------------------------------
# Test 5: Generator LLM failure — graph swallows exception, returns fallback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generator_llm_failure_produces_fallback_answer(tmp_path: Path) -> None:
    """When the Generator node's LLM raises, the graph must NOT propagate the
    exception — it returns the error-fallback answer with confidence 0.0 and
    a steps_taken entry starting with 'generator:error:'.
    """
    settings = _mock_settings(tmp_path)
    doc = _make_doc()
    retriever_mock, _ = _make_retriever_node_mock(doc)

    # Router and grader succeed normally; only the generator LLM call raises.
    router_chain = MagicMock()
    router_chain.ainvoke = AsyncMock(
        return_value=_RouterOutput(
            query_type="factual", retrieval_strategy="hybrid", reasoning="ok"
        )
    )

    grader_chain = MagicMock()
    grader_chain.batch = MagicMock(return_value=[_GradeDoc(score=0.9, reasoning="relevant")])

    # Generator chain raises to simulate Azure throttling
    gen_chain = MagicMock()
    gen_chain.ainvoke = AsyncMock(side_effect=Exception("Azure throttled"))

    critic_chain = MagicMock()
    critic_chain.ainvoke = AsyncMock(
        return_value=_CriticOutput(
            hallucination_risk=0.1, unsupported_claims=[], reasoning="grounded"
        )
    )

    schema_map: dict[str, MagicMock] = {
        "_RouterOutput": router_chain,
        "_GradeDoc": grader_chain,
        "_GeneratorOutput": gen_chain,
        "_CriticOutput": critic_chain,
    }

    llm_mock = MagicMock()
    llm_mock.with_structured_output.side_effect = lambda schema: schema_map.get(
        schema.__name__, MagicMock()
    )

    with (
        patch("src.graph.builder.AzureChatOpenAI", return_value=llm_mock),
        patch("src.graph.builder.retriever_node", retriever_mock),
    ):
        compiled = await build_graph(settings=settings, retriever=MagicMock())
        # Must not raise — generator error handler swallows the exception
        terminal = await _collect_terminal_state(compiled, _initial_state())

    assert terminal["answer"] == "I encountered an error generating a response."
    assert terminal["confidence"] == pytest.approx(0.0)
    steps: list[str] = terminal.get("steps_taken", [])
    assert any(s.startswith("generator:error:") for s in steps)
