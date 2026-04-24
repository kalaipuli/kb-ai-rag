"""Ingestion pipeline: load → chunk → embed → upsert → BM25 index."""

import time
from pathlib import Path

import structlog
from pydantic import BaseModel

from src.config import Settings
from src.exceptions import IngestionError
from src.ingestion.bm25_store import BM25Store
from src.ingestion.embedder import Embedder
from src.ingestion.loaders.local_loader import LocalFileLoader
from src.ingestion.splitter import DocumentSplitter
from src.ingestion.vector_store import QdrantVectorStore

logger = structlog.get_logger(__name__)


class PipelineResult(BaseModel):
    """Summary of a completed ingestion pipeline run."""

    docs_processed: int
    """Number of raw document pages/files successfully loaded."""

    chunks_created: int
    """Total chunks produced after splitting and quality filtering."""

    errors: list[str]
    """Per-file error messages; pipeline continues on individual failures."""

    duration_ms: float
    """Wall-clock time for the full pipeline run in milliseconds."""


async def run_pipeline(data_dir: Path, settings: Settings) -> PipelineResult:
    """Run the full document ingestion pipeline.

    Stages:
    1. Load files from ``data_dir`` with ``LocalFileLoader``.
    2. Split into chunks with ``DocumentSplitter``.
    3. Embed with ``Embedder`` (async batched Azure OpenAI calls).
    4. Ensure Qdrant collection and upsert all points.
    5. Build BM25 index and persist to disk.

    Per-file errors are collected in ``PipelineResult.errors`` rather than
    aborting the run.
    """
    pipeline_start = time.monotonic()
    errors: list[str] = []

    # --- Stage 1: Load -------------------------------------------------------
    t0 = time.monotonic()
    loader = LocalFileLoader(data_dir=data_dir)
    try:
        documents = await loader.load()
    except Exception as exc:
        logger.error("pipeline_load_failed", error=str(exc))
        errors.append(f"Load stage failed: {exc}")
        documents = []

    load_ms = (time.monotonic() - t0) * 1000
    logger.info(
        "pipeline_load_complete",
        doc_count=len(documents),
        duration_ms=round(load_ms, 1),
    )

    if not documents:
        return PipelineResult(
            docs_processed=0,
            chunks_created=0,
            errors=errors,
            duration_ms=(time.monotonic() - pipeline_start) * 1000,
        )

    # --- Stage 2: Split -------------------------------------------------------
    t0 = time.monotonic()
    splitter = DocumentSplitter(settings=settings)
    chunks = splitter.split(documents)
    split_ms = (time.monotonic() - t0) * 1000
    logger.info(
        "pipeline_split_complete",
        chunk_count=len(chunks),
        duration_ms=round(split_ms, 1),
    )

    if not chunks:
        logger.warning("pipeline_no_chunks_after_split")
        return PipelineResult(
            docs_processed=len(documents),
            chunks_created=0,
            errors=errors,
            duration_ms=(time.monotonic() - pipeline_start) * 1000,
        )

    # --- Stage 3: Embed -------------------------------------------------------
    t0 = time.monotonic()
    embedder = Embedder(settings=settings)
    try:
        embedded_chunks = await embedder.embed_chunks(chunks)
    except Exception as exc:
        logger.error("pipeline_embed_failed", error=str(exc))
        errors.append(f"Embedding stage failed: {exc}")
        return PipelineResult(
            docs_processed=len(documents),
            chunks_created=len(chunks),
            errors=errors,
            duration_ms=(time.monotonic() - pipeline_start) * 1000,
        )

    embed_ms = (time.monotonic() - t0) * 1000
    logger.info(
        "pipeline_embed_complete",
        embedded_count=len(embedded_chunks),
        duration_ms=round(embed_ms, 1),
    )

    # --- Stage 4: Qdrant upsert -----------------------------------------------
    t0 = time.monotonic()
    vector_store = QdrantVectorStore(settings=settings)
    upsert_failed = False
    try:
        await vector_store.ensure_collection()
        await vector_store.upsert(embedded_chunks)
    except IngestionError as exc:
        logger.error("pipeline_upsert_failed", error=str(exc))
        errors.append(f"Upsert stage failed: {exc}")
        upsert_failed = True
    finally:
        await vector_store.close()

    upsert_ms = (time.monotonic() - t0) * 1000
    logger.info(
        "pipeline_upsert_complete",
        duration_ms=round(upsert_ms, 1),
    )

    if upsert_failed:
        # Qdrant is empty — skip BM25 to avoid inconsistent state.
        return PipelineResult(
            docs_processed=len(documents),
            chunks_created=len(chunks),
            errors=errors,
            duration_ms=(time.monotonic() - pipeline_start) * 1000,
        )

    # --- Stage 5: BM25 index --------------------------------------------------
    t0 = time.monotonic()
    bm25_store = BM25Store(index_path=Path(settings.bm25_index_path))
    try:
        bm25_store.build(embedded_chunks)
        bm25_store.save()
    except Exception as exc:
        logger.error("pipeline_bm25_failed", error=str(exc))
        errors.append(f"BM25 stage failed: {exc}")
        return PipelineResult(
            docs_processed=len(documents),
            chunks_created=len(embedded_chunks),
            errors=errors,
            duration_ms=(time.monotonic() - pipeline_start) * 1000,
        )
    bm25_ms = (time.monotonic() - t0) * 1000
    logger.info(
        "pipeline_bm25_complete",
        duration_ms=round(bm25_ms, 1),
    )

    total_ms = (time.monotonic() - pipeline_start) * 1000
    logger.info(
        "pipeline_complete",
        docs_processed=len(documents),
        chunks_created=len(embedded_chunks),
        error_count=len(errors),
        total_duration_ms=round(total_ms, 1),
    )

    return PipelineResult(
        docs_processed=len(documents),
        chunks_created=len(embedded_chunks),
        errors=errors,
        duration_ms=total_ms,
    )


if __name__ == "__main__":
    import asyncio

    from src.config import get_settings

    _settings = get_settings()
    result = asyncio.run(run_pipeline(Path(_settings.data_dir), _settings))
    logger.info("pipeline_complete", **result.model_dump())
