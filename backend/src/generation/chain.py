"""Generation chain: LCEL pipeline wrapping HybridRetriever + AzureChatOpenAI.

Implements ADR-007: replaces the legacy ``RetrievalQA`` abstraction with an
explicit LCEL composition (prompt | llm | parser).  Retrieved documents flow
through the explicit data path; confidence scoring reads scores directly from
document metadata rather than a side-channel attribute.
"""

import json
import math
from collections.abc import AsyncGenerator

import structlog
from langchain_core.callbacks import (
    AsyncCallbackManagerForRetrieverRun,
    CallbackManagerForRetrieverRun,
)
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.retrievers import BaseRetriever
from langchain_openai import AzureChatOpenAI
from pydantic import PrivateAttr

from src.config import Settings
from src.exceptions import GenerationError
from src.generation.prompts import QA_PROMPT
from src.retrieval.retriever import HybridRetriever
from src.schemas.generation import Citation, GenerationResult

logger = structlog.get_logger(__name__)


class KBRetriever(BaseRetriever):
    """Bridges HybridRetriever to LangChain's BaseRetriever interface.

    The synchronous ``_get_relevant_documents`` is intentionally unimplemented
    because the full stack is async-only.  Only ``_aget_relevant_documents``
    should be called.

    Retrieved document metadata includes a ``"score"`` key carrying the
    cross-encoder logit, which the ``GenerationChain`` uses for confidence
    scoring without any side-channel attribute.
    """

    _hybrid: HybridRetriever = PrivateAttr()
    _k: int | None = PrivateAttr(default=None)
    _filters: dict[str, str] | None = PrivateAttr(default=None)

    def __init__(
        self,
        hybrid_retriever: HybridRetriever,
        k: int | None = None,
        filters: dict[str, str] | None = None,
    ) -> None:
        super().__init__()
        self._hybrid = hybrid_retriever
        self._k = k
        self._filters = filters

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> list[Document]:
        raise NotImplementedError("Use async only")

    async def _aget_relevant_documents(
        self,
        query: str,
        *,
        run_manager: AsyncCallbackManagerForRetrieverRun,
    ) -> list[Document]:
        results = await self._hybrid.retrieve(
            query,
            k=self._k,
            filters=self._filters,
        )
        return [
            Document(
                page_content=r.text,
                metadata={
                    "chunk_id": r.metadata["chunk_id"],
                    "filename": r.metadata["filename"],
                    "source_path": r.metadata["source_path"],
                    "page_number": (
                        r.metadata["page_number"] if r.metadata["page_number"] != -1 else None
                    ),
                    "score": r.score,
                },
            )
            for r in results
        ]


class GenerationChain:
    """Orchestrates retrieval → LLM generation → citation extraction.

    The LLM is constructed once at ``__init__`` time so Azure credentials are
    validated eagerly and the client is not re-created on every ``generate``
    call.

    The LCEL pipeline is ``QA_PROMPT | llm | StrOutputParser()``.  Retrieved
    documents are fetched explicitly before invoking the pipeline so that
    citation and confidence data are available in the same call without any
    side-channel.
    """

    def __init__(
        self,
        settings: Settings,
        hybrid_retriever: HybridRetriever,
    ) -> None:
        self._settings = settings
        self._hybrid = hybrid_retriever
        self._llm = AzureChatOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key.get_secret_value(),  # type: ignore[arg-type]
            azure_deployment=settings.azure_chat_deployment,
            api_version=settings.azure_openai_api_version,
            temperature=0,
        )

    def _build_citations(self, docs: list[Document]) -> tuple[list[Citation], float]:
        """Build deduplicated citations and compute sigmoid confidence.

        Extracts chunk metadata from each document, deduplicates by chunk_id,
        and computes confidence as sigmoid of the mean cross-encoder score for
        the top-3 documents.

        Args:
            docs: Retrieved documents with metadata including ``chunk_id``,
                ``filename``, ``source_path``, ``page_number``, and ``score``.

        Returns:
            Tuple of (deduplicated citations list, confidence in [0.0, 1.0]).
        """
        seen: set[str] = set()
        citations: list[Citation] = []
        for doc in docs:
            cid = str(doc.metadata.get("chunk_id", ""))
            if cid and cid not in seen:
                seen.add(cid)
                raw_page = doc.metadata.get("page_number")
                raw_score = doc.metadata.get("score")
                citations.append(
                    Citation(
                        chunk_id=cid,
                        filename=str(doc.metadata.get("filename", "")),
                        source_path=str(doc.metadata.get("source_path", "")),
                        page_number=(
                            int(raw_page) if raw_page is not None and int(raw_page) != -1 else None
                        ),
                        retrieval_score=(float(raw_score) if raw_score is not None else None),
                    )
                )

        scores = [float(doc.metadata.get("score", 0.0)) for doc in docs[:3]]
        if scores:
            mean_score = sum(scores) / len(scores)
            confidence = float(1.0 / (1.0 + math.exp(-mean_score)))
        else:
            confidence = 0.0
        confidence = max(0.0, min(1.0, confidence))

        return citations, confidence

    async def generate(
        self,
        query: str,
        k: int | None = None,
        filters: dict[str, str] | None = None,
    ) -> GenerationResult:
        """Run retrieval then LLM generation and return a structured result.

        Args:
            query: Natural-language question.
            k: Optional override for the number of retrieved chunks.
            filters: Optional payload filters forwarded to the dense retriever.

        Returns:
            ``GenerationResult`` with answer, deduplicated citations, and
            a confidence score in [0.0, 1.0].

        Raises:
            GenerationError: Wraps any exception raised by the LLM or
                retrieval pipeline.
        """
        kb_retriever = KBRetriever(
            hybrid_retriever=self._hybrid,
            k=k,
            filters=filters,
        )

        try:
            docs = await kb_retriever.ainvoke(query)

            # Build numbered context string matching the [N] citation convention
            # in the system prompt.
            context = "\n\n".join(f"[{i + 1}] {doc.page_content}" for i, doc in enumerate(docs))

            # LCEL pipeline: prompt → llm → string parser
            chain = QA_PROMPT | self._llm | StrOutputParser()
            answer: str = await chain.ainvoke({"context": context, "question": query})

            citations, confidence = self._build_citations(docs)

        except GenerationError:
            raise
        except Exception as exc:
            logger.error("generation_failed", query_len=len(query), error=str(exc))
            raise GenerationError(f"Generation failed: {exc}") from exc

        logger.info(
            "generation_complete",
            query_len=len(query),
            citation_count=len(citations),
            confidence=round(confidence, 4),
        )
        return GenerationResult(
            query=query,
            answer=answer,
            citations=citations,
            confidence=confidence,
            retrieved_contexts=[doc.page_content for doc in docs],
        )

    async def astream_generate(
        self,
        query: str,
        k: int | None = None,
        filters: dict[str, str] | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream generation as SSE events.

        Yields three event types in order:
        - ``token``: one per LLM output token
        - ``citations``: all citations + confidence + chunks_retrieved count
        - ``done``: signals end of stream
        """
        kb_retriever = KBRetriever(
            hybrid_retriever=self._hybrid,
            k=k,
            filters=filters,
        )

        try:
            docs = await kb_retriever.ainvoke(query)

            context = "\n\n".join(f"[{i + 1}] {doc.page_content}" for i, doc in enumerate(docs))

            citations, confidence = self._build_citations(docs)

            chain = QA_PROMPT | self._llm | StrOutputParser()
            async for token in chain.astream({"context": context, "question": query}):
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

            yield f"data: {json.dumps({'type': 'citations', 'citations': [c.model_dump() for c in citations], 'confidence': round(confidence, 4), 'chunks_retrieved': len(docs)})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except GenerationError:
            raise
        except Exception as exc:
            logger.error("generation_stream_failed", query_len=len(query), error=str(exc))
            raise GenerationError(f"Generation failed: {exc}") from exc
